""" Test fixtures """

import pytest


@pytest.fixture
def mock_bigiq_pool(monkeypatch):
    """Set: BIGIQ license pool"""
    monkeypatch.setenv("BIGIQ_LICENSE_POOL", "test_pool")
    monkeypatch.setenv("BIGIQ_UTILITY_KEY", "")
    monkeypatch.setenv("BIGIQ_UTILITY_OFFER", "")


@pytest.fixture
def mock_bigiq_utility(monkeypatch):
    """Set: BIGIQ utility key and offer"""
    monkeypatch.setenv("BIGIQ_LICENSE_POOL", "")
    monkeypatch.setenv("BIGIQ_UTILITY_KEY", "test_utility_key")
    monkeypatch.setenv("BIGIQ_UTILITY_OFFER", "test_utility_offer")


@pytest.fixture
def mock_bigiq_all(monkeypatch):
    """Set: BIGIQ license pool, utility key and offer"""
    monkeypatch.setenv("BIGIQ_LICENSE_POOL", "test_pool")
    monkeypatch.setenv("BIGIQ_UTILITY_KEY", "test_utility_key")
    monkeypatch.setenv("BIGIQ_UTILITY_OFFER", "test_utility_offer")


@pytest.fixture
def mock_bigiq_all_missing(monkeypatch):
    """Remove: BIGIQ license pool, utility key and offer"""
    monkeypatch.setenv("BIGIQ_LICENSE_POOL", "")
    monkeypatch.setenv("BIGIQ_UTILITY_KEY", "")
    monkeypatch.setenv("BIGIQ_UTILITY_OFFER", "")


@pytest.fixture
def mock_main_env_variables(monkeypatch):
    """Set: Azure and BIGIQ env vars"""
    monkeypatch.setenv("AZURE_RESOURCE_GROUP", "my_group")
    monkeypatch.setenv("AZURE_VMSS_NAME", "my_vmss_name")
    monkeypatch.setenv("BIGIQ_ADDRESS", "10.1.1.1")
    monkeypatch.setenv("BIGIQ_USERNAME", "admin")
    monkeypatch.setenv("BIGIQ_PASSWORD", "some_password")


@pytest.fixture
def mock_main_env_variables_missing(monkeypatch):
    """Remove: Azure and BIGIQ env vars"""
    monkeypatch.delenv("AZURE_RESOURCE_GROUP", raising=False)
    monkeypatch.delenv("AZURE_VMSS_NAME", raising=False)
    monkeypatch.delenv("BIGIQ_ADDRESS", raising=False)
    monkeypatch.delenv("BIGIQ_USERNAME", raising=False)
    monkeypatch.delenv("BIGIQ_PASSWORD", raising=False)


@pytest.fixture
def mock_tenant_variables(monkeypatch):
    """Set: TENANT and AZURE_VMSS_NAME vars"""
    monkeypatch.setenv("TENANT", "my_tenant")
    monkeypatch.setenv("AZURE_VMSS_NAME", "my_vmss_name")


@pytest.fixture
def mock_tenant_variables_missing(monkeypatch):
    """Remove: TENANT and AZURE_VMSS_NAME vars"""
    monkeypatch.delenv("TENANT", raising=False)
    monkeypatch.delenv("AZURE_VMSS_NAME", raising=False)
