""" Test get_property function """
# pylint: disable=unused-argument
# pylint: disable=line-too-long
# pylint: disable=import-error

from timer_trigger_revoke import get_property

def test_get_property():
    """Test: function get_property

    Assertions
    ----------
    - response should match specified return value
    """
    assert get_property({"key": "value"}, "key", "default") == "value"

def test_get_property_default():
    """Test: function get_property

    Assertions
    ----------
    - response should match default return value
    """
    assert get_property({"key": "value"}, "foo", "default") == "default"
