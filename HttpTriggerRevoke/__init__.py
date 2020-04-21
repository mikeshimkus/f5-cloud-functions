# pylint: disable=import-error
# pylint: disable=no-name-in-module
# pylint: disable=unused-variable

import os
import logging
import json
import azure.functions as func

from msrestazure.azure_active_directory import MSIAuthentication
from azure.mgmt.resource import SubscriptionClient
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient

from f5sdk.bigiq import ManagementClient
from f5sdk.bigiq.licensing import AssignmentClient
from f5sdk.bigiq.licensing.pools import MemberManagementClient
from f5sdk.logger import Logger


def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    try:
        req_body = req.get_json()
    except Exception as _e:
        return func.HttpResponse(
            'Exception parsing JSON body: %s' % _e,
            status_code=400
        )

    # set variables
    operation = req_body['operation']
    group = os.environ['AZURE_RESOURCE_GROUP']
    resource = os.environ['AZURE_VMSS_NAME']

    # get vmss instance ip addresses
    # Create MSI authentication - requires a system managed identity assigned to this function
    credentials = MSIAuthentication()

    # Create a Subscription Client
    subscription_client = SubscriptionClient(credentials)
    subscription = next(subscription_client.subscriptions.list())
    subscription_id = subscription.subscription_id

    # Create Management clients
    resourceClient = ResourceManagementClient(credentials, subscription_id)
    computeClient = ComputeManagementClient(credentials, subscription_id)
    networkClient = NetworkManagementClient(credentials, subscription_id)

    # Create a dictionary of instances
    provisioned = []
    licensed = []

    vmss = computeClient.virtual_machine_scale_set_vms.list(group, resource)
    for instance in vmss:
        instance_name = instance.name
        instance_id = instance.instance_id
        vmss_vm = computeClient.virtual_machine_scale_set_vms.get(group, resource, instance.instance_id)
        vmss_vm_provisioning_state = vmss_vm.provisioning_state

        try: 
            nic = resourceClient.resources.get_by_id(
                instance.network_profile.network_interfaces[0].id,
                api_version='2017-12-01')
            ip_reference = nic.properties['ipConfigurations'][0]['properties']
            private_ip = ip_reference['privateIPAddress']
            mac_address = nic.properties['macAddress']
        except AttributeError:
            provisioning_state = None
            private_ip = None
            mac_address = None

        provisioned.append({
            'instance_name': instance_name, 
            'instance_id': instance_id, 
            'provisioning_state': vmss_vm_provisioning_state, 
            'private_ip': private_ip, 
            'mac_address': mac_address.replace("-", ":")})

    logging.info("Instance dictionary: " + str(provisioned))


    # get license assignments
    mgmt_client = ManagementClient(
        os.environ['BIGIQ_ADDRESS'],
        user=os.environ['BIGIQ_USERNAME'],
        password=os.environ['BIGIQ_PASSWORD'])

    # create assignment client and member management client
    assignment_client = AssignmentClient(mgmt_client)
    member_mgmt_client = MemberManagementClient(mgmt_client)

    assignments = assignment_client.list()
    assignments = assignments['items']
    
    if not assignments:
        raise Exception('Unable to locate any BIG-IQ assignments!')

    for assignment in assignments:  
        licensed.append({          
            'private_ip': assignment['deviceAddress'], 
            'mac_address': assignment['macAddress']})

    logging.info("Assignment dictionary: " + str(licensed))

    for licensed_thing in licensed[:]:
        for provisioned_thing in provisioned:
            if licensed_thing['mac_address'] == provisioned_thing['mac_address'] and \
                provisioned_thing['provisioning_state'] == 'Succeeded' or \
                    provisioned_thing['provisioning_state'] == 'Creating':
                        licensed.remove(licensed_thing)

    logging.info("Final dictionary: " + str(licensed))

    if licensed:
        for unlicensed_thing in licensed:
            # let my Cameron go
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

    return 'Great!'
