import pytest

from cfme.markers.env import EnvironmentMarker
from cfme.markers.env_markers import _param_check
from cfme.utils import testgen
from cfme.utils.log import logger
from cfme.utils.pytest_shortcuts import fixture_filter


def parametrize(metafunc, argnames, argvalues, *args, **kwargs):
    """parametrize wrapper that calls :py:func:`_param_check`, and only parametrizes when needed

    This can be used in any place where conditional parametrization is used.

    """
    if _param_check(metafunc, argnames, argvalues):
        metafunc.parametrize(argnames, argvalues, *args, **kwargs)
    elif 'appliance' in metafunc.fixturenames:
        try:
            # hack to pass trough in case of a failed param_check
            # where it sets a custom message
            metafunc.function.uncollect
        except AttributeError:
            pytest.mark.uncollect(
                reason="provider was not parametrized did you forget --use-provider?"
            )(metafunc.function)


def appliances(metafunc, app_types, fixture_name='appliance'):
    """ Gets appliances based on given (+ global) filters

    Note:
        Using the default 'function' scope, each test will be run individually for each appliance
        before moving on to the next test. To group all tests related to single appliance together,
        parametrize tests in the 'module' scope.

    Note:
        testgen for providers now requires the usage of test_flags for collection to work.
        Please visit http://cfme-tests.readthedocs.org/guides/documenting.html#documenting-tests
        for more details.
    """
    argnames = []
    argvalues = []
    idlist = []

    # supported_providers are the ones "supported" in the supportability.yaml file. It will
    # be a list of DataProvider objects and will be filtered based upon what the test has asked for
    holder = metafunc.config.pluginmanager.get_plugin('appliance-holder')
    current_appliance = holder.held_appliance
    argnames.append(fixture_name)
    for app_type in app_types:
        idlist.append(app_type)
        if app_type == current_appliance.type:
            argvalues.append([current_appliance])
        else:
            msg = (f'No appliance of such type available. needed {app_type}, '
                   f'exists {current_appliance.type}')
            argvalues.append(pytest.param(None, marks=pytest.mark.uncollect(reason=msg)))
    return argnames, argvalues, idlist


class ApplianceEnvironmentMarker(EnvironmentMarker):
    NAME = 'appliance'
    DEFAULT = 'default'
    CHOICES = ['default', 'multi-region', 'dummy', 'dev', 'pod', 'upgraded']

    def process_env_mark(self, metafunc):

        # organize by fixture_name kwarg to the marker
        # iter_markers returns most local mark first, maybe don't need override
        marks_by_fixture = self.get_closest_kwarg_markers(metafunc.definition)
        if marks_by_fixture is None:
            # let's add appliance marker if it's absent

            # dummy is added here in order to be collected/uncollected in order to test
            # collection and integrity
            marks_by_fixture = {self.DEFAULT: pytest.mark.appliance([self.DEFAULT, 'dummy'],
                                                                    scope='module')}
        # process each mark, defaulting fixture_name
        for fixture_name, mark in marks_by_fixture.items():

            # mark is either the lowest marker (automatic override), or has custom fixture_name
            logger.debug(f'Parametrizing appliance env mark {mark}')
            args = mark.args
            kwargs = mark.kwargs.copy()
            scope = kwargs.pop('scope', 'function')
            indirect = kwargs.pop('indirect', False)
            filter_unused = kwargs.pop('filter_unused', True)
            gen_func = kwargs.pop('gen_func', appliances)

            mark_choice = args[0] if args else self.DEFAULT

            app_types = []
            if isinstance(mark_choice, (list, tuple)):
                app_types = mark_choice
            elif mark_choice == testgen.ALL:
                app_types = self.CHOICES
            elif mark_choice == testgen.ONE:
                app_types.append(self.DEFAULT)
            elif mark_choice == testgen.NONE:
                return
            else:
                app_types.append(self.DEFAULT)
            kwargs['app_types'] = app_types

            argnames, argvalues, idlist = gen_func(metafunc, **kwargs)
            # Filter out argnames that aren't requested on the metafunc test item,
            # so not all tests need all fixtures to run, and tests not using gen_func's
            # fixtures aren't parametrized.
            if filter_unused:
                argnames, argvalues = fixture_filter(metafunc, argnames, argvalues)
                # See if we have to parametrize at all after filtering
            parametrize(metafunc, argnames, argvalues, indirect=indirect, ids=idlist, scope=scope)
