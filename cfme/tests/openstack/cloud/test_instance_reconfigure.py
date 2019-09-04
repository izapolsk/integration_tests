import pytest
from cfme import test_requirements
from cfme.cloud.provider.openstack import OpenStackProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.utils.generators import random_vm_name
from cfme.utils.wait import wait_for


pytestmark = [
    pytest.mark.usefixtures('setup_provider'),
    pytest.mark.long_running,
    pytest.mark.tier(2),
    pytest.mark.provider([OpenStackProvider], required_fields=['templates'], selector=ONE_PER_TYPE),
    test_requirements.multi_region,
    test_requirements.reconfigure,
]


def reconfigure_vm(vm, config):
    """Reconfigure VM to have the supplies config."""
    reconfigure_request = vm.reconfigure(config)
    wait_for(reconfigure_request.is_succeeded, timeout=360, delay=45,
        message="confirm that vm was reconfigured")
    wait_for(
        lambda: vm.configuration == config, timeout=360, delay=45,
        fail_func=vm.refresh_relationships,
        message="confirm that config was applied. Hardware: {}, disks: {}"
                .format(vars(config.hw), config.disks))


@pytest.fixture(scope='function')
def full_vm(appliance, provider, full_template):
    """This fixture is function-scoped, because there is no un-ambiguous way how to search for
    reconfigure request in UI in situation when you have two requests for the same reconfiguration
    and for the same VM name. This happens if you run test_vm_reconfig_add_remove_hw_cold and then
    test_vm_reconfig_add_remove_hw_hot or vice versa. Making thix fixture function-scoped will
    ensure that the VM under test has a different name each time so the reconfigure requests
    are unique as a result."""
    vm = appliance.collections.cloud_instances.instantiate(random_vm_name(context='reconfig'),
                                                           provider,
                                                           full_template.name)
    vm.create_on_provider(find_in_cfme=True, allow_skip="default")
    vm.refresh_relationships()

    yield vm

    vm.cleanup_on_provider()


def test_vm_reconfigure_from_global_region(setup_multi_region_cluster,
                                           multi_region_cluster,
                                           activate_global_appliance,
                                           setup_remote_provider,
                                           full_vm):
    """
    reconfigure a VM via CA

    Polarion:
        assignee: izapolsk
        casecomponent: Infra
        initialEstimate: 1/3h
        testSteps:
            1. Have a VM created in the provider in the Remote region which is
               subscribed to Global.
            2. Reconfigure the VM using the Global appliance.
        expectedResults:
            1.
            2.
            3. VM reconfigured, no errors.
    """
    pass