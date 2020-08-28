"""Azure BIGIQ license pool revocation script"""
# pylint: disable=no-name-in-module
# pylint: disable=unused-argument
# pylint: disable=line-too-long
# pylint: disable=too-many-locals

import os
import logging
import datetime

from msrestazure.azure_active_directory import MSIAuthentication

import azure.functions as func
from azure.mgmt.resource import SubscriptionClient, ResourceManagementClient
from azure.mgmt.compute import ComputeManagementClient

from f5sdk.bigiq import ManagementClient
from f5sdk.bigiq.licensing import AssignmentClient
from f5sdk.bigiq.licensing.pools import MemberManagementClient, UtilityOfferingMembersClient


def get_property(obj, key, default):
    """Check if object has a property"""
    try:
        ret = obj[key]
    except KeyError:
        ret = default
    return ret


def get_pool_lic_type():
    """Return BIGIQ license pool type"""
    if os.environ['BIGIQ_LICENSE_POOL'] and \
        not os.environ['BIGIQ_UTILITY_KEY'] and \
            not os.environ['BIGIQ_UTILITY_OFFER']:
        licensing_mode = 'pool'
    elif os.environ['BIGIQ_UTILITY_KEY'] and \
        os.environ['BIGIQ_UTILITY_OFFER'] and \
            not os.environ['BIGIQ_LICENSE_POOL']:
        licensing_mode = 'utility'
    else:
        raise Exception('You must provide either a registration key pool name or a utility license key and offer name, but not both!')
    return licensing_mode


def get_vmss_instances(group, resource, compute_client, resource_client):
    """Get a list of all instances in specified vm scale set"""
    provisioned = []
    vmss = compute_client.virtual_machine_scale_set_vms.list(group, resource, expand='instanceView')
    for instance in vmss:
        instance_name = instance.name
        instance_id = instance.instance_id
        vmss_vm_provisioning_state = instance.provisioning_state
        logging.info('Provisioning state for instance ' + instance_name + ' is: ' + vmss_vm_provisioning_state)
        if vmss_vm_provisioning_state in ['Creating', 'Succeeded', 'Updating']:
            nic = resource_client.resources.get_by_id(instance.network_profile.network_interfaces[0].id, api_version='2017-12-01')
            ip_reference = nic.properties['ipConfigurations'][0]['properties']
            private_ip = get_property(ip_reference, 'privateIPAddress', 'creating')
            mac_address = get_property(nic.properties, 'macAddress', 'creating')
            provisioned.append({
                'instance_name': instance_name,
                'instance_id': instance_id,
                'provisioning_state': vmss_vm_provisioning_state,
                'private_ip': private_ip,
                'mac_address': mac_address.replace("-", ":")})
    logging.info('Instance dictionary: %s', str(provisioned))
    return provisioned


def get_bigiq_assignments(mgmt_client):
    """Get all BIG-IQ license assignments"""
    # create assignment client
    assignment_client = AssignmentClient(mgmt_client)
    assignments = assignment_client.list()
    assignments = assignments['items']
    if not assignments:
        logging.info('Unable to locate any BIG-IQ assignments!')
    return assignments


def filter_tenant_assignments(assignments):
    """Keep only the license assignments for our tenant"""
    licensed = []
    if os.getenv("TENANT") is None:
        raise KeyError('TENANT is undefined and is required')
    if os.getenv("AZURE_VMSS_NAME") is None:
        raise KeyError('AZURE_VMSS_NAME is undefined and is required')
    for assignment in assignments:
        if assignment['tenant']:
            if os.environ['TENANT'] == assignment['tenant'] or \
                (os.environ['TENANT'] == os.environ['AZURE_VMSS_NAME'] and \
                    len(assignment['tenant'][assignment['tenant'].rfind(os.environ['TENANT']):assignment['tenant'].rfind('-')]) == len(os.environ['TENANT'])):
                licensed.append({
                    'private_ip': assignment['deviceAddress'],
                    'mac_address': assignment['macAddress'],
                    'id': assignment['id'],
                    'tenant': assignment['tenant']})
    if not licensed:
        logging.info('Unable to locate any licensed devices for this tenant!')
    else:
        logging.info('Assignment dictionary: %s', str(licensed))
    return licensed


def filter_provisioning_state(tenant_filtered, provisioned):
    """Remove licenses from revoke list when provisioning state: Creating, Succeeded, or Updating and mac address matches a licensed instance"""
    for licensed_device in tenant_filtered[:]:
        for provisioned_device in provisioned:
            if provisioned_device['mac_address'] != 'creating' and \
                licensed_device['mac_address'] == provisioned_device['mac_address']:
                tenant_filtered.remove(licensed_device)
    if not tenant_filtered:
        logging.info('No licenses are eligible for revocation!')
    else:
        logging.info('Revocation dictionary: %s', str(tenant_filtered))
    return tenant_filtered


def revoke(licensing_mode, state_filtered, mgmt_client):
    """Revoke specified licenses on BIGIQ"""
    if licensing_mode == 'pool':
        member_mgmt_client = MemberManagementClient(mgmt_client)
        for unlicensed_device in state_filtered:
            member_mgmt_client.create(
                config={
                    'licensePoolName': os.environ['BIGIQ_LICENSE_POOL'],
                    'command': 'revoke',
                    'address': unlicensed_device['private_ip'],
                    'assignmentType': 'UNREACHABLE',
                    'macAddress': unlicensed_device['mac_address'],
                    'hypervisor': 'azure'
                }
            )
    elif licensing_mode == 'utility':
        utility_members_client = UtilityOfferingMembersClient(
            mgmt_client,
            pool_name=os.environ['BIGIQ_UTILITY_KEY'],
            offering_name=os.environ['BIGIQ_UTILITY_OFFER']
        )
        for unlicensed_device in state_filtered:
            utility_members_client.delete(
                name=unlicensed_device['id'],
                config={
                    'assignmentType': 'UNREACHABLE',
                    'macAddress': unlicensed_device['mac_address'],
                    'hypervisor': 'azure'
                }
            )
    else:
        raise Exception('Invalid BIG-IQ info specified, check app settings!')


def main(mytimer: func.TimerRequest) -> None:
    """Discover vms and revoke if necessary unused licenses on BIGIQ"""
    utc_timestamp = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat()
    logging.info('Python timer trigger function ran at %s', utc_timestamp)

    # Create MSI authentication - requires a system managed identity assigned to this function
    credentials = MSIAuthentication()

    # Create Azure subscription client
    subscription_client = SubscriptionClient(credentials)
    subscription = next(subscription_client.subscriptions.list())
    subscription_id = subscription.subscription_id

    # Create Azure management clients
    resource_client = ResourceManagementClient(credentials, subscription_id)
    compute_client = ComputeManagementClient(credentials, subscription_id)

    # Set variables
    group = os.environ['AZURE_RESOURCE_GROUP']
    resource = os.environ['AZURE_VMSS_NAME']
    mgmt_client = ManagementClient(
        os.environ['BIGIQ_ADDRESS'],
        user=os.environ['BIGIQ_USERNAME'],
        password=os.environ['BIGIQ_PASSWORD'])
    licensing_mode = get_pool_lic_type()
    provisioned = get_vmss_instances(group, resource, compute_client, resource_client)
    assignments = get_bigiq_assignments(mgmt_client)
    tenant_filtered = filter_tenant_assignments(assignments)
    state_filtered = filter_provisioning_state(tenant_filtered, provisioned)
    # Revoke licenses
    revoke(licensing_mode, state_filtered, mgmt_client)
    logging.info('Finished license revocation.')
