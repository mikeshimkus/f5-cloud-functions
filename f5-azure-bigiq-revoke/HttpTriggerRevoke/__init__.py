# pylint: disable=import-error
# pylint: disable=no-name-in-module
# pylint: disable=unused-variable

import os
import logging
import json
import azure.functions as func

from msrestazure.azure_active_directory import MSIAuthentication
from azure.mgmt.resource import SubscriptionClient, ResourceManagementClient
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient

from f5sdk.bigiq import ManagementClient
from f5sdk.bigiq.licensing import AssignmentClient
from f5sdk.bigiq.licensing.pools import MemberManagementClient, UtilityOfferingMembersClient


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    try:
        req_body = req.get_json()
    except Exception as _e:
        return func.HttpResponse(
            'Exception parsing JSON body: %s' % _e,
            status_code=400
        )

    # Set variables
    operation = req_body['operation']
    group = os.environ['AZURE_RESOURCE_GROUP']
    resource = os.environ['AZURE_VMSS_NAME']

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

    # Create MSI authentication - requires a system managed identity assigned to this function
    credentials = MSIAuthentication()

    # Create Azure subscription client
    subscription_client = SubscriptionClient(credentials)
    subscription = next(subscription_client.subscriptions.list())
    subscription_id = subscription.subscription_id

    # Create Azure management clients
    resourceClient = ResourceManagementClient(credentials, subscription_id)
    computeClient = ComputeManagementClient(credentials, subscription_id)
    networkClient = NetworkManagementClient(credentials, subscription_id)

    # Create dictionaries of provisioned, licensed, and revoked instances
    provisioned = []
    licensed = []
    revoked = []

    # Get a list of all instances in our vm scale set
    vmss = computeClient.virtual_machine_scale_set_vms.list(group, resource)
    for instance in vmss:
        instance_name = instance.name
        instance_id = instance.instance_id
        vmss_vm = computeClient.virtual_machine_scale_set_vms.get(group, resource, instance.instance_id)
        vmss_vm_provisioning_state = vmss_vm.provisioning_state
        logging.info('Provisioning state for instance ' + instance_name + ' is: ' + vmss_vm_provisioning_state)

        if vmss_vm_provisioning_state in ['Succeeded', 'Updating', 'Failed']: 
            nic = resourceClient.resources.get_by_id(
                instance.network_profile.network_interfaces[0].id,
                api_version='2017-12-01')
            ip_reference = nic.properties['ipConfigurations'][0]['properties']
            private_ip = ip_reference['privateIPAddress']
            mac_address = nic.properties['macAddress']
        elif vmss_vm_provisioning_state in ['Creating']: 
            private_ip = 'creating'
            mac_address = 'creating'
        else:
            private_ip = 'deleting'
            mac_address = 'deleting'

        provisioned.append({
            'instance_name': instance_name, 
            'instance_id': instance_id, 
            'provisioning_state': vmss_vm_provisioning_state, 
            'private_ip': private_ip, 
            'mac_address': mac_address.replace("-", ":")})

    logging.info("Instance dictionary: " + str(provisioned))


    # Get all BIG-IQ license assignments
    mgmt_client = ManagementClient(
        os.environ['BIGIQ_ADDRESS'],
        user=os.environ['BIGIQ_USERNAME'],
        password=os.environ['BIGIQ_PASSWORD'])

    # create assignment client
    assignment_client = AssignmentClient(mgmt_client)
    assignments = assignment_client.list()
    assignments = assignments['items']
    
    if not assignments:
        raise Exception('Unable to locate any BIG-IQ assignments!')

    # Keep only the license assignments for our tenant
    for assignment in assignments:  
        if assignment['tenant'] and assignment['tenant'] in os.environ['TENANT']:
            licensed.append({          
                'private_ip': assignment['deviceAddress'], 
                'mac_address': assignment['macAddress'],
                'id': assignment['id'],
                'tenant': assignment['tenant']})

    if not licensed:
        raise Exception('Unable to locate any licensed devices for this tenant!')
    else:
        revoked = licensed
        logging.info("Assignment dictionary: " + str(licensed))
        
    # Revoke licenses for failed, deleting, or missing instances
    for licensed_thing in revoked[:]:
        for provisioned_thing in provisioned:
            if licensed_thing['mac_address'] == provisioned_thing['mac_address'] and \
                    provisioned_thing['provisioning_state'] in ['Creating', 'Succeeded', 'Updating']:
                        revoked.remove(licensed_thing)

    if not revoked:
        raise Exception('No licenses are eligible for revocation!')
    else:
        logging.info("Revocation dictionary: " + str(revoked))

    if licensing_mode == 'pool':
        member_mgmt_client = MemberManagementClient(mgmt_client)

        for unlicensed_thing in revoked:
            member_mgmt_client.create(
                config={
                    'licensePoolName': os.environ['BIGIQ_LICENSE_POOL'],
                    'command': 'revoke',
                    'address': unlicensed_thing['private_ip'],
                    'assignmentType': 'UNREACHABLE',
                    'macAddress': unlicensed_thing['mac_address'],
                    'hypervisor': 'azure'
                }
            )
    elif licensing_mode == 'utility':
        utility_members_client = UtilityOfferingMembersClient(
            mgmt_client,
            pool_name=os.environ['BIGIQ_UTILITY_KEY'],
            offering_name=os.environ['BIGIQ_UTILITY_OFFER']
        )

        for unlicensed_thing in revoked:
            utility_members_client.delete(
                name=unlicensed_thing['id'],
                config={
                    'assignmentType': 'UNREACHABLE',
                    'macAddress': unlicensed_thing['mac_address'],
                    'hypervisor': 'azure'
                }
            )
    else:
        raise Exception('Invalid BIG-IQ info specified, check app settings!')

    return func.HttpResponse(
            'Finished license revocation.',
            status_code=200
        )
