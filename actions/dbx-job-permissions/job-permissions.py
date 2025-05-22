import json
import sys
import requests
import argparse


def convert_ud_permissions_to_dbx_json(ud_permission_json):
    """
    Convert user-defined permissions to Databricks Jobs API JSON format.

    Args:
        ud_permission_json (dict): User-defined permissions JSON.

    Returns:
        str: Databricks Jobs API JSON representation of access control list.

    Raises:
        ValueError: If the 'is_owner' permission has more than one user or service principal assigned.
        ValueError: If the group is not either "users" or "admins".
    """
    access_control_list_json = {"access_control_list": []}

    for permission, values in ud_permission_json["permissions"].items():
        if permission == "is_owner" and len(values["users"]) + len(values["groups"]) + (1 if values["service_principal_name"] else 0) > 1:
            raise ValueError("The 'is_owner' permission can only have one user or service principal assigned.")

        for user in values["users"]:
            access_control_list_json["access_control_list"].append(
                {"user_name": user, "permission_level": permission.upper()}
            )
        for group in values["groups"]:
            if group not in ["users", "admins"]:
                raise ValueError(f"{group} is not a valid group")
            access_control_list_json["access_control_list"].append(
                {"group_name": group, "permission_level": permission.upper()}
            )
        for spn in values["service_principal_name"]:
            access_control_list_json["access_control_list"].append(
                {"service_principal_name": spn, "permission_level": permission.upper()}
            )

    return json.dumps(access_control_list_json, indent=2)


def update_job_permissions(job_id, access_control_list, databricks_url, databricks_token, dry_run=False):
    """
    Update the permissions for a specific job.

    Args:
        job_id (str): Job ID to update permissions for.
        access_control_list (str): Databricks Jobs API JSON representation of access control list.
        databricks_url (str): Databricks URL.
        databricks_token (str): Databricks access token.
        dry_run (bool, optional): Whether to perform a dry run. Defaults to False.

    Raises:
        Exception: If the HTTP response code is not 200.
    """
    # Remove the last slash if it exists from the URL using rstrip
    databricks_url = databricks_url.rstrip("/")
    headers = {
        'Authorization': f'Bearer {databricks_token}',
        'Content-Type': 'application/json'
    }

    if databricks_url.startswith("https://"):
        dbx_api_url = f"{databricks_url}/api/2.0/permissions/jobs/{job_id}"
    elif databricks_url.startswith("http://"):
        dbx_api_url = f"{databricks_url.replace('http://', 'https://')}/api/2.0/permissions/jobs/{job_id}"
    else:
        dbx_api_url = f"https://{databricks_url}/api/2.0/permissions/jobs/{job_id}"

    print(f"Updating permissions for Job ID: {job_id}")
    # This PUT request overrides the existing permissions
    if dry_run:
        print(f"DRY RUN DETECTED: Not updating permissions for Job ID: {job_id}")
        return

    response = requests.put(dbx_api_url, headers=headers, data=access_control_list)

    if response.status_code != 200:
        raise Exception(f"{response.json()['error_code']} :: {response.json()['message']}")

    print("SUCCESS")


def get_all_job_ids(databricks_url, databricks_token):
    """
    Get all job IDs from a provided Databricks workspace.

    Args:
        databricks_url (str): Databricks URL.
        databricks_token (str): Databricks Access Token.

    Returns:
        list: List of all job IDs in the Databricks workspace.

    Raises:
        Exception: If the HTTP response code is not 200.
    """
    job_ids = []

    # Sanitize Databricks URL
    databricks_url = databricks_url.rstrip("/")
    headers = {
        'Authorization': f'Bearer {databricks_token}',
        'Content-Type': 'application/json'
    }

    # Create the Databricks API URL
    if databricks_url.startswith("https://"):
        dbx_api_url = f"{databricks_url}/api/2.1/jobs/list"
    elif databricks_url.startswith("http://"):
        dbx_api_url = f"{databricks_url.replace('http://', 'https://')}/api/2.1/jobs/list"
    else:
        dbx_api_url = f"https://{databricks_url}/api/2.1/jobs/list"

    job_response_limit = 25
    params = {"limit": job_response_limit}
    print("Getting all Job IDs from Databricks...")
    while True:
        response = requests.get(dbx_api_url, headers=headers, params=params)

        if response.status_code != 200:
            raise Exception(f"{response.json()['error_code']} :: {response.json()['message']}")

        for job in response.json().get("jobs", []):
            job_ids.append(job["job_id"])

        if not response.json().get("has_more"):
            break
        print(f"Retrieved {len(job_ids)} Job IDs so far. More jobs exist. Getting more...")
        params["offset"] = params.get("offset", 0) + job_response_limit

    print("SUCCESS")
    return job_ids


def main():
    """
    Main program entry point.
    """
    # Set argument variables
    parser = argparse.ArgumentParser(description='Add permissions to jobs')
    parser.add_argument('-t', '--databricks-token', type=str, help='Databricks Access Token')
    parser.add_argument('-u', '--databricks-url', type=str, help='Databricks URL containing the jobs')
    parser.add_argument('-p', '--jobs-permissions-json', type=str, help='Path to JSON file containing job permissions')
    parser.add_argument('--dry-run', action='store_true', help='Dry run, do not apply changes')
    # --all-jobs and --job-id cannot be used together
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-a', '--all-jobs', action='store_true', help='Add permissions to all jobs')
    group.add_argument('-j', '--job-id', type=str, help='Add permissions to a single Job ID')
    args = parser.parse_args()

    try:
        with open(args.jobs_permissions_json, "r") as file:
            ud_json = json.load(file)
        access_control_list = convert_ud_permissions_to_dbx_json(ud_json)
        if args.job_id:
            update_job_permissions(args.job_id, access_control_list, args.databricks_url, args.databricks_token, args.dry_run)
        else:
            job_id_list = get_all_job_ids(args.databricks_url, args.databricks_token)
            if len(job_id_list) == 0:
                print("No jobs found to update. Exiting...")
                sys.exit(0)
            print(f"Found {len(job_id_list)} jobs. Updating permissions for all jobs...")
            for job_id in job_id_list:
                update_job_permissions(job_id, access_control_list, args.databricks_url, args.databricks_token, args.dry_run)

    except FileNotFoundError:
        print(f"ERROR: Jobs permissions JSON file not found: {args.jobs_permissions_json}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"ERROR: Invalid JSON format in jobs permissions JSON file: {args.jobs_permissions_json}")
        sys.exit(1)
    except ValueError as ve:
        print(f"ERROR: {str(ve)}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
