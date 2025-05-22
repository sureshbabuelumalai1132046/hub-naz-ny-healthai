import argparse
import json

logger = LM.get_logger(__name__)


def get_job_id(job_config: dict, jobs_in_workspace: list) -> dict:
    """
    This method is used to override the job ID in the run_job_task field of a run job task. It takes the job_config
    and list of jobs as input and returns the modified job_config with the job ID overridden.
    """

    # convert to dictionary for constant lookup
    jobs_dict = {
        job["settings"]["name"]: job["job_id"]
        for jobs in jobs_in_workspace
        for job in jobs["jobs"]
    }

    changes_made = False

    # iterate over tasks in job
    for task in job_config["tasks"]:
        # get job name from ID field to override
        job_name = task.get("run_job_task", {}).get("job_id")
        if job_name:
            logger.info(
                f"Found job {job_name} reference in job {job_config['name']} task {task['task_key']}"
            )
            # if the job name matches get the ID and set that as the run task job ID
            if job_name in jobs_dict:
                logger.info(
                    f"Found job {job_name} with job_id {jobs_dict[job_name]} in workspace"
                )
                task["run_job_task"]["job_id"] = jobs_dict[job_name]
                logger.info(
                    f"Updated job_id {job_name} in run_job_task to {jobs_dict[job_name]} in job {job_config['name']} task {task['task_key']}"
                )

                # set changes made to true to indicate that the job has been updated
                changes_made = True
            else:
                logger.error(f"Job {job_name} not found in workspace")
                exit(1)
        # error if run_job_task specified but no job ID is provided
        elif "run_job_task" in task:
            logger.error(
                f"Invalid job config: run_job_task specified but job_id not found in task {task['task_key']}"
            )
            exit(1)

    # log if no changes were made
    if not changes_made:
        logger.info(
            f"Run job task not found in {job_config['name']}, no changes made to the job"
        )

    return job_config


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-d",
        "--dbx_instance_url",
        required=True,
        help="URL for the databricks instance",
    )
    parser.add_argument(
        "-t",
        "--dbx_token",
        required=True,
        help="Personal access token for the databricks instance",
    )
    parser.add_argument(
        "-j", "--job-path", required=True, help="Path to the job JSON file."
    )

    args = parser.parse_args()

    # Load job JSON file
    with open(args.job_path) as f:
        job = json.load(f)

    # fetch jobs in the DBX workspace
    db_conn = Databricks(args.dbx_instance_url, args.dbx_token)
    jobs_in_workspace = db_conn.list_jobs()

    job = get_job_id(job, jobs_in_workspace)

    # Save the updated job back to the JSON file
    with open(args.job_path, "w") as f:
        json.dump(job, f)
