from get_run_job_task_job_id import get_job_id
import pytest
import json


def get_json_config(file_name):
    with open(file_name, "r") as file_config:
        return json.loads(file_config.read())


@pytest.fixture
def jobs_in_workspace():
    return [
        {
            "jobs": [
                {"job_id": 1234, "settings": {"name": "run_job_task_test"}},
                {"job_id": 5678, "settings": {"name": "brand_test"}},
            ]
        }
    ]


def test_get_job_id_no_run_job_task(jobs_in_workspace):
    """
    This test asserts that the job config remains unchanged since there is no run job task.
    """
    job = get_json_config("./tests/test_jsons/job_config_no_run_job_task.json")

    assert job == get_job_id(job, jobs_in_workspace)


def test_get_job_id_run_job_task(jobs_in_workspace):
    """
    This test asserts that the job ID (name) in the run job task is updated to the correct job ID.
    """
    job = get_json_config("./tests/test_jsons/job_config_run_job_task.json")

    updated_job = get_job_id(job, jobs_in_workspace)
    job_id = updated_job["tasks"][0]["run_job_task"]["job_id"]

    assert isinstance(job_id, int)
    assert job_id == 5678


def test_get_job_id_multiple_run_job_tasks(jobs_in_workspace):
    """
    This test asserts that the job ID (name) in the run job task is updated to the correct job ID for multiple tasks.
    """
    job = get_json_config("./tests/test_jsons/job_config_run_job_tasks.json")

    updated_job = get_job_id(job, jobs_in_workspace)
    first_job_id = updated_job["tasks"][0]["run_job_task"]["job_id"]
    second_job_id = updated_job["tasks"][1]["run_job_task"]["job_id"]

    assert isinstance(first_job_id, int)
    assert first_job_id == 1234
    assert isinstance(second_job_id, int)
    assert second_job_id == 5678


def test_get_job_id_invalid_run_job_task(jobs_in_workspace):
    """
    This test asserts that an exception is raised when job ID (name) is not configured under run job task.
    """
    job = get_json_config("./tests/test_jsons/job_config_invalid_run_job_task.json")

    with pytest.raises(SystemExit):
        get_job_id(job, jobs_in_workspace)


def test_get_job_id_missing_job_id(jobs_in_workspace):
    """
    This test asserts that an exception is raised when job ID (name) is not found in the workspace.
    """

    job = {
        "name": "invalid_job_id",
        "webhook_notifications": {},
        "timeout_seconds": 3600,
        "schedule": {
            "quartz_cron_expression": "0 0 1 * * ?",
            "timezone_id": "America/Chicago",
            "pause_status": "PAUSED",
        },
        "max_concurrent_runs": 1,
        "tasks": [
            {
                "task_key": "test",
                "run_job_task": {"job_id": "missing_job"},
            }
        ],
    }

    with pytest.raises(SystemExit):
        get_job_id(job, jobs_in_workspace)
