import argparse
import logging
import sys
import traceback as tb
from datetime import datetime
from tabulate import tabulate

from cfme.utils.path import log_path
from cfme.utils.providers import list_provider_keys, get_mgmt


def parse_cmd_line():
    parser = argparse.ArgumentParser(argument_default=None)
    parser.add_argument('--nic-template',
                        help='NIC Name template to be removed', default="test", type=str)
    parser.add_argument('--pip-template',
                        help='PIP Name template to be removed', default="test", type=str)
    parser.add_argument('--days-old',
                        help='--days-old argument to find stack items older than X days ',
                        default="7", type=int)
    parser.add_argument("--output", dest="output", help="target file name, default "
                                                        "'cleanup_azure.log' in "
                                                        "utils.path.log_path",
                        default=log_path.join('cleanup_azure.log').strpath)
    parser.add_argument('--remove-unused-blobs',
                        help='Removal of unused blobs', default=True)
    args = parser.parse_args()
    return args


def azure_cleanup(nic_template, pip_template, days_old):
        logger.info('azure_cleanup.py, NICs, PIPs, Disks and Stack Cleanup')
        logger.info("Date: {}".format(datetime.now()))
        try:
            for prov_key in list_provider_keys('azure'):
                mgmt = get_mgmt(prov_key)
                logger.info("----- Provider: {} -----".format(prov_key))

                # removing stale nics
                nic_list = mgmt.list_free_nics(nic_template)
                if nic_list:
                    logger.info("Removing Nics with the name '{}':".format(nic_template))
                    logger.info(tabulate(tabular_data=[[nic] for nic in nic_list], headers=[
                        "Name"], tablefmt='orgtbl'))
                    mgmt.remove_nics_by_search(nic_template)
                else:
                    logger.info("No '{}' NICs were found".format(nic_template))

                # removing public ips
                pip_list = mgmt.list_free_pip(pip_template)
                if pip_list:
                    logger.info("Removing Public IPs with the name '{}':".
                                 format(pip_template))
                    logger.info(tabulate(tabular_data=[[pip] for pip in pip_list], headers=[
                        "Name"], tablefmt='orgtbl'))
                    mgmt.remove_pips_by_search(pip_template)
                else:
                    logger.info("No '{}' Public IPs were found".format(pip_template))

                # removing stale stacks
                stack_list = mgmt.list_stack(days_old=days_old)
                if stack_list:
                    logger.info("Removing empty Stacks:")
                    removed_stacks = []
                    for stack in stack_list:
                        if mgmt.is_stack_empty(stack):
                            removed_stacks.append(stack)
                            mgmt.delete_stack(stack)
                    logger.info(tabulate(tabular_data=[[st] for st in removed_stacks], headers=[
                        "Name"], tablefmt='orgtbl')) if len(removed_stacks) > 0 else None
                else:
                    logger.info("No stacks older than '{}' days were found".format(
                        days_old))

                """
                Blob removal section
                """
                logger.info("\nRemoving 'bootdiagnostics-test*' containers\n")
                bootdiag_list = []
                for container in mgmt.container_client.list_containers():
                    if container.name.startswith('bootdiagnostics-test'):
                        bootdiag_list.append(container.name)
                        mgmt.container_client.delete_container(
                            container_name=container.name)
                logger.info(tabulate(tabular_data=[[disk] for disk in bootdiag_list], headers=[
                    "Name"], tablefmt='orgtbl'))
                logger.info("Removing unused blobs and disks")
                removed_disks = mgmt.remove_unused_blobs()
                if len(removed_disks['Managed']) > 0:
                    logger.info('Managed disks:')
                    logger.info(tabulate(tabular_data=removed_disks['Managed'], headers="keys",
                                          tablefmt='orgtbl'))
                if len(removed_disks['Unmanaged']) > 0:
                    logger.info('Unmanaged blobs:')
                    logger.info(tabulate(tabular_data=removed_disks['Unmanaged'], headers="keys",
                                          tablefmt='orgtbl'))
            return 0
        except Exception:
            logger.info("Something bad happened during Azure cleanup\n")
            logger.info(tb.format_exc())
            return 1


if __name__ == "__main__":
    args = parse_cmd_line()

    # setup logging
    formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
    file_handler = logging.FileHandler(args.output)
    file_handler.setFormatter(formatter)

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    logger.addHandler(stdout_handler)
    logger.addHandler(file_handler)

    sys.exit(azure_cleanup(args.nic_template, args.pip_template, args.days_old))
