import pytest
from check_for_timeout import check_for_timeout


def test_check_for_timeout():
    """
    This method contains both negative and positive tests for the check_for_timeout method.
    """

    # test with timeout configured
    job_config_with_timeout = {
        "name": "test_job",
        "webhook_notifications": {},
        "timeout_seconds": 3600,
    }
    assert check_for_timeout(job_config_with_timeout) == None

    # test with timeout set to 0 (which means no timeout)
    job_config_default_of_zero = {
        "name": "test_job",
        "webhook_notifications": {},
        "timeout_seconds": 0,
    }
    with pytest.raises(SystemExit):
        check_for_timeout(job_config_default_of_zero)

    # test with no timeout configured (Databricks defaults to 0)
    job_config_no_timeout = {"name": "test_job", "webhook_notifications": {}}
    with pytest.raises(SystemExit):
        check_for_timeout(job_config_no_timeout)
