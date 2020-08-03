""" Test BIG-IQ license pool type """
# pylint: disable=unused-argument
# pylint: disable=line-too-long
# pylint: disable=import-error

import pytest
from timer_trigger_revoke import get_pool_lic_type
from timer_trigger_revoke import filter_tenant_assignments
from timer_trigger_revoke import filter_provisioning_state


def test_pool_lic_type(mock_bigiq_pool):
    """Test: function pool_lic_type

    Assertions
    ----------
    - response should match mocked return value
    """
    assert get_pool_lic_type() == "pool"


def test_utility_lic_type(mock_bigiq_utility):
    """Test: function pool_lic_type

    Assertions
    ----------
    - response should match mocked return value
    """
    assert get_pool_lic_type() == "utility"


def test_get_pool_lic_type_key_error(mock_bigiq_all_missing):
    """Test: function pool_lic_type

    Assertions
    ----------
    - response should match returned Exception value
    """
    with pytest.raises(Exception) as execinfo:
        _ = get_pool_lic_type()
    assert "You must provide either a registration key pool name or a utility license key and offer name, but not both!" in str(execinfo.value)


def test_get_pool_lic_type_exception(mock_bigiq_all):
    """Test: function pool_lic_type

    Assertions
    ----------
    - response should match returned Exception value
    """
    with pytest.raises(Exception) as excinfo:
        _ = get_pool_lic_type()
    assert "You must provide either a registration key pool name or a utility license key and offer name, but not both!" in str(excinfo.value)


def test_filter_tenant_assignments_match(mock_tenant_variables):
    """Test: function filter_tenant_assignment

    Assertions
    ----------
    - response should match mocked return value
    """
    assert filter_tenant_assignments([{"tenant": "my_tenant", "deviceAddress": "10.1.1.1", "macAddress": "00:0a:95:9d:68:16", "id": "some-long-id-number"}]) == [{'id': 'some-long-id-number', 'mac_address': '00:0a:95:9d:68:16', 'private_ip': '10.1.1.1', 'tenant': 'my_tenant'}]


def test_filter_tenant_assignments_no_match(mock_tenant_variables):
    """Test: function filter_tenant_assignment

    Assertions
    ----------
    - response should match mocked return value
    """
    assert filter_tenant_assignments([{"tenant": "some_tenant", "deviceAddress": "10.1.1.1", "macAddress": "00:0a:95:9d:68:16", "id": "some-long-id-number"}]) == []


def test_filter_tenant_assignments_no_tenant(mock_tenant_variables_missing):
    """Test: function filter_tenant_assignment

    Assertions
    ----------
    - response should match expected returned KeyError value
    """
    with pytest.raises(KeyError) as keyinfo:
        _ = filter_tenant_assignments([])
    assert "TENANT is undefined and is required" in str(keyinfo)


def test_filter_provisioning_state_match():
    """Test: function filter_provisioning_state

    Assertions
    ----------
    - response should match mocked return value
    """
    assert filter_provisioning_state([{'id': 'some-long-id-number', 'mac_address': '00:0a:95:9d:68:16', 'private_ip': '10.1.1.1', 'tenant': 'my_tenant'}], [{'mac_address': '00:0a:95:9d:68:16', 'provisioning_state': 'Creating'}]) == []


def test_filter_provisioning_state_no_match():
    """Test: function filter_provisioning_state

    Assertions
    ----------
    - response should match mocked return value
    """
    assert filter_provisioning_state([{'id': 'some-long-id-number', 'mac_address': '00:0a:95:9d:68:16', 'private_ip': '10.1.1.1', 'tenant': 'my_tenant'}], []) == [{'id': 'some-long-id-number', 'mac_address': '00:0a:95:9d:68:16', 'private_ip': '10.1.1.1', 'tenant': 'my_tenant'}]
