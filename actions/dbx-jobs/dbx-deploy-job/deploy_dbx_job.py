import os
import argparse
import json
import logging
import requests

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def update_libraries(dbx_job_config, default_libraries_config):
    """
    Given a databricks job configuration, adds on default libraries
    If libraries already exist, it adds on default libraries that do not exist
    """
    if "libraries" not in dbx_job_config:
        dbx_job_config["libraries"] = default_libraries_config["libraries"]
    else:
        # ensure that default libraries get installed before feature specific libraries
        for library in reversed(default_libraries_config["libraries"]):
            if library not in dbx_job_config["libraries"]:
                dbx_job_config["libraries"] = [library] + dbx_job_config["libraries"]


def create_job_config(job_config, default_libraries_config, env):
    """
    Used to modify the databricks job config to prepare it for deployment
    Should hold all needed modifications.
    Current modifications consist of adding default libraries
    """
    if "dbx_job" in job_config:
        dbx_job_config = (
            job_config["dbx_job"]
            if env not in job_config["dbx_job"]
            else job_config["dbx_job"][env]
        )
    else:
        dbx_job_config = job_config

    if (
        "include_default_libraries" in job_config
        and job_config["include_default_libraries"]
    ):
        if "tasks" in dbx_job_config:
            for job_task in dbx_job_config["tasks"]:
                logger.info(f"Adding libraries to task {job_task['task_key']}")
                update_libraries(job_task, default_libraries_config)
        else:
            logger.info(f"Updating libraries for job {dbx_job_config['name']}")
            update_libraries(dbx_job_config, default_libraries_config)

    return dbx_job_config
    
class Databricks:
    def __init__(self, instance_url, token):
        self.instance_url = instance_url.rstrip('/')
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    def list_jobs(self):
        url = f"{self.instance_url}/api/2.1/jobs/list"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return [response.json()]

    def deploy_job(self, job_config):
        job_name = job_config.get("name")
        existing_jobs = self.list_jobs()

        # Check if job already exists
        job_id = None
        for jobs_group in existing_jobs:
            for job in jobs_group.get("jobs", []):
                if job["settings"]["name"] == job_name:
                    job_id = job["job_id"]
                    break

        if job_id:
            # Update existing job
            url = f"{self.instance_url}/api/2.1/jobs/update"
            payload = {
                "job_id": job_id,
                **job_config
            }
            response = requests.post(url, headers=self.headers, data=json.dumps(payload))
            response.raise_for_status()
            logging.info(f"Updated job: {job_name} with job_id: {job_id}")
        else:
            # Create new job
            url = f"{self.instance_url}/api/2.1/jobs/create"
            response = requests.post(url, headers=self.headers, data=json.dumps(job_config))
            response.raise_for_status()
            job_id = response.json().get("job_id")
            logging.info(f"Created job: {job_name} with job_id: {job_id}")

        return job_id


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
        "-j",
        "--job_configs",
        required=True,
        help="Space seperated string of config file paths",
    )
    parser.add_argument(
        "-l",
        "--default_libraries",
        required=True,
        help="Path to a config file set with default libraries",
    )
    parser.add_argument(
        "-e",
        "--env",
        nargs="?",
        default="",
        help="Target environment mapped in the config file",
    )
    parser.add_argument(
        "--dry_run",
        action="store_true",
        help="To run as normal without deploying, required for action testing",
    )

    args = parser.parse_args()

    # Default if a library config wasn't provided, will ensure the job won't fail
    default_libraries_config = {"libraries": []}
    if args.default_libraries != "":
        with open(args.default_libraries, "r") as default_libs:
            default_libraries_config = json.loads(default_libs.read())

    job_id_mapping = {}
    db_conn = Databricks(args.dbx_instance_url, args.dbx_token)

    # Need this for action integration testing
    fake_job_id = 0
    for job_config_path in args.job_configs.strip().split(" "):
        logger.info(f"Starting deployment process for {job_config_path}")
        with open(job_config_path, "r") as job_config_info:
            job_config = json.loads(job_config_info.read())

        dbx_job_config = create_job_config(
            job_config, default_libraries_config, args.env
        )

        if args.dry_run:
            logger.info(f"Dry run specified, not deploying jobs")
        # If there aready are dbx job ids from a previous deployment and the env exists
        if "dbx_job_id" in job_config and args.env in job_config["dbx_job_id"]:
            # dry run setting is needed to do action tests
            job_id = (
                job_config["dbx_job_id"][args.env]
                if args.dry_run
                else db_conn.deploy_job(
                    dbx_job_config, job_id=int(job_config["dbx_job_id"][args.env])
                )
            )
        else:
            if args.dry_run:
                job_id = fake_job_id
                fake_job_id += 1
            else:
                # Utilize Job name instead
                job_id = db_conn.deploy_job(dbx_job_config)
        job_id_mapping[job_config_path] = job_id

    with open(os.environ["GITHUB_OUTPUT"], "a") as github_output:
        job_id_mapping_string = " ".join(
            [
                f"{str(file_name)}:{job_id}"
                for file_name, job_id in job_id_mapping.items()
            ]
        )
        print(f"job_ids={job_id_mapping_string}", file=github_output)
