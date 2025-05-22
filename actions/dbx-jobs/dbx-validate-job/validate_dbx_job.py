import argparse
import json
import os
import re
from datetime import datetime, timezone

from typing import Any, Dict, List

import pandas as pd

import requests

logger = LogManager().get_logger("Job Validation")

def clean_dbx_hostname(hostname: str) -> str:
    """
    Clean the Databricks hostname by removing 'https://' prefix and everything after '.net'

    hostname (str) The Databricks hostname to be cleaned
    Returns (str) The cleaned Databricks hostname
    """
    if hostname.startswith("https://"):
        hostname = hostname[8:]
    if ".net" in hostname:
        hostname = hostname.split(".net")[0] + ".net"
    return hostname


def extract_workspace_id(hostname: str) -> str:
    """
    Extract the Databricks workspace ID from the Databricks hostname

    hostname (str) The Databricks hostname to be parsed
    Returns (str) The Databricks workspace ID
    """
    # Define the regular expression pattern to match the workspace ID
    pattern = r"adb-(\d+)\.7\.azuredatabricks\.net"

    # Search for the pattern in the URL
    match = re.search(pattern, hostname)

    # If a match is found, return the workspace ID
    if match:
        return match.group(1)
    else:
        return None

def fetch_request(base_uri: str, endpoint: str, headers: Dict[str, str], params: Dict[str, Any]) -> requests.Response:
    """
    Makes a request to the Databricks Jobs API.
    
    Args:
        base_uri (str): The base URI of the Databricks workspace.
        endpoint (str): The endpoint of the Databricks Jobs API.
        headers (Dict[str, str]): The headers for the request.
        params (Dict[str, Any]): The parameters for the request.

    Returns:
        requests.Response: The response from the Databricks Jobs API.
    """
    return requests.get("https://" + base_uri + endpoint, headers=headers, params=params)

def fetch_job_id(base_uri: str, api_token: str, job_name: str) -> str:
    """
    Fetches the job ID for a given job name from the Databricks Jobs API.

    Args:
        base_uri (str): The base URI of the Databricks workspace.
        api_token (str): The API token for authentication.
        job_name (str): The name of the job to fetch the ID for.

    Returns:
        str: The job ID if found, otherwise an empty string.
    """
    endpoint = "/api/2.1/jobs/list"
    headers = {"Authorization": f"Bearer {api_token}"}

    all_data = []

    params = {
        "name": job_name,
    }
    while True:
        response = fetch_request(base_uri, endpoint, headers, params)
        response_json = response.json()

        data = []

        if response_json.get("jobs") is None:
            return ""

        for job in response_json["jobs"]:
            data.append(
                {
                    "job_id": job["job_id"],
                }
            )

        all_data.extend(data)
        df = pd.DataFrame(all_data)

        if response_json.get("has_more") == True:
            next_page_token = response_json.get("next_page_token")
            params["page_token"] = next_page_token
        else:
            break

    df = pd.DataFrame(all_data)

    if df.empty:
        return ""

    return df.iloc[0]["job_id"]


def fetch_latest_job_run_status(
    base_uri: str, api_token: str, job_id: str, pull_request_timestamp: datetime
) -> str:
    """
    Fetches the latest job run status for a given job ID from the Databricks Jobs API.

    Args:
        base_uri (str): The base URI of the Databricks workspace.
        api_token (str): The API token for authentication.
        job_id (str): The ID of the job to fetch the run status for.
        pull_request_timestamp (datetime): The timestamp to filter job runs starting from this time.

    Returns:
        str: The result state of the latest job run if found, otherwise an empty string.
    """
    endpoint = "/api/2.1/jobs/runs/list"
    headers = {"Authorization": f"Bearer {api_token}"}

    all_data = []

    params = {
        "job_id": job_id,
        "completed_only": True,
        "start_time_from": pull_request_timestamp.timestamp() * 1000,
    }
    while True:
        response = fetch_request(base_uri, endpoint, headers, params)
        response_json = response.json()

        data = []

        if response_json.get("runs") is None:
            return ""

        for run in response_json["runs"]:
            start_time_ms = run["start_time"]
            start_time_seconds = start_time_ms / 1000
            start_time_readable = datetime.fromtimestamp(start_time_seconds).strftime("%Y-%m-%d %H:%M:%S")
            end_time_ms = run["end_time"]
            end_time_seconds = end_time_ms / 1000
            end_time_readable = datetime.fromtimestamp(end_time_seconds).strftime("%Y-%m-%d %H:%M:%S")
            data.append(
                {
                    "job_id": run["job_id"],
                    "run_id": run["run_id"],
                    "result_state": run["state"].get("result_state"),
                    "start_time": start_time_readable,
                    "end_time": end_time_readable,
                }
            )

        all_data.extend(data)
        df = pd.DataFrame(all_data)

        if response_json.get("has_more") == True:
            next_page_token = response_json.get("next_page_token")
            params["page_token"] = next_page_token
        else:
            break

    df = pd.DataFrame(all_data)

    if df.empty:
        return ""

    df["start_time"] = pd.to_datetime(df["start_time"])
    df["end_time"] = pd.to_datetime(df["end_time"])
    df_sorted = df.sort_values(by="end_time", ascending=False)
    latest_record = df_sorted.iloc[0]

    return latest_record["result_state"]


## Main
parser = argparse.ArgumentParser(
    prog="Validate job on Databricks",
    description="This script takes a json DBX job config file and validates that that the job has been run in the dev environment.",
)
parser.add_argument("-n", "--databricks-hostname", required=True, help="The Databricks Hostname to run SQL on")
parser.add_argument("-t", "--databricks-token", required=True, help="Databricks Token for authentication")
parser.add_argument("-f", "--file-path", required=True, help="File path to job to be validated")
parser.add_argument("-p", "--pull-request-timestamp", required=True, help="Pull request timestamp")

args = parser.parse_args()

if args.file_path.lower().endswith(".json") == False:
    logger.error("Changed file is not a job config")
    exit(0)
else:
    logger.info("Changed file is a job config")

with open(args.file_path) as json_file:
    job_config = json.load(json_file)
job_name = job_config.get("name")

pull_request_timestamp = datetime.strptime(args.pull_request_timestamp, "%Y-%m-%dT%H:%M:%SZ").astimezone(timezone.utc)
logger.info(f"Validating job: {job_name}. Pull request timestamp: {pull_request_timestamp}.")

# Clean the databricks hostname if needed
dbx_hostname = clean_dbx_hostname(hostname=args.databricks_hostname)
databricks_token = args.databricks_token

# Validate that the job has been run successfully in the dev environment since the pull request
job_id = fetch_job_id(dbx_hostname, databricks_token, job_name)
if job_id == "":
    logger.info(f"Job {job_name} does not exist in the dev environment.")
    exit(1)

run_status = fetch_latest_job_run_status(dbx_hostname, databricks_token, job_id, pull_request_timestamp)

if run_status == "":
    logger.error(f"Job {job_name} has not been run in the dev environment since the pull request was opened.")
    exit(1)
elif run_status == "SUCCESS":
    logger.info(f"Job {job_name} has been run successfully in the dev environment since the pull request was opened.")
    exit(0)
else:
    logger.error(
        f"Job {job_name} has not been run successfully in the dev environment since the pull request was opened. Last result state: {run_status}"
    )
    exit(1)
