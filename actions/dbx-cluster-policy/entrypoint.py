#!/usr/local/bin/python

import os, subprocess, json, sys, requests, argparse

###---------Functions----------###
def authenticate_databricks_cli(auth_filename: str):
    """
    This method authenticates the Databricks CLI with a Databricks instance.
    Args:
        auth_filename (str): filename to be used for the temporary auth file
    """
    with open(auth_filename, "x") as tmpFile:
        tmpFile.write(args.DBX_ACCESS_TOKEN)
    try:
        subprocess.check_call(
            ["databricks", "configure", "-f", auth_filename, "--host", args.DBX_INSTANCE]
        )
    except Exception as e:
        print(str(e))
        sys.exit(1)
    finally:
        os.remove(auth_filename)


def build_json_for_cli(cluster_policy_path: str) -> dict:
    """
    This method builds a JSON dict that will be used to pass into the Cluster CLI.
    Args:
        cluster_policy_path (str): Path to cluster policy
    Returns:
        dict: Json Dict representation of cluster policy based on file path
    """
    filename = os.path.basename(cluster_policy_path)
    print("Making json for policy: " + filename)
    policy_name = os.path.splitext(filename)[0]
    print("Policy will be named: " + policy_name)
    with open(cluster_policy_path, "r+") as local_policy_json_file:
        policy_definition = json.load(local_policy_json_file)
        local_json = {"name": policy_name, "definition": json.dumps(policy_definition)}
        return local_json


def upload_new_cluster_policy(cluster_policy_json: dict):
    """
    This method uploads a cluster policy to Databricks using the Databricks CLI
    Args:
        cluster_policy_json (dict): JSON dict that contains the cluster policy
    """
    print("Attempting to upload cluster policy....")
    try:
        if args.DRY_RUN == "false":
            subprocess.check_call(
                [
                    "databricks",
                    "cluster-policies",
                    "create",
                    "--json",
                    json.dumps(cluster_policy_json),
                ]
            )
        else:
            print("DRY RUN DETECTED, not actually creating policy")
    except Exception as e:
        print(str(e))
        sys.exit(1)


def get_policy_id(policy_name: str):
    """
    This method uses the Databricks CLI to get the Policy ID from the name of a Cluster Policy
    Args:
        policy_name (str): Cluster policy name to look up
    Returns:
        str: Policy Id if the cluster policy exists otherwise it returns an empty string
    """
    list_policy_output_f = subprocess.check_output(
        ["databricks", "cluster-policies", "list", "--output", "JSON"]
    )
    list_policy_output = str(list_policy_output_f.decode(encoding="utf-8"))
    policy_json = json.loads(list_policy_output)
    # if no policies exist, assume no policy id
    if policy_json["total_count"] == 0:
        print("No existing cluster policies found in given Databricks Instance.")
        return ""
    for policy in policy_json["policies"]:
        if policy["name"] == policy_name:
            print(
                "Policy " + policy_name + " found with policy Id " + policy["policy_id"]
            )
            return policy["policy_id"]
    return ""


def update_existing_cluster_policy(policy_id: str, cluster_policy_json: dict):
    """
    This method uses the Databricks CLI to update an existing cluster policy in Databricks
    Args:
        cluster_policy_json (dict): JSON dict that contains the cluster policy
        policy_id (str): Cluster policy id to update
    Returns:
        dict: Json Dict representation of cluster policy based on file path
    """
    print("Updating " + cluster_policy_json["name"] + " using policy id " + policy_id)
    # updating existing json to have policy id for dbx cli requirements
    local_json = {"policy_id": policy_id}
    cluster_policy_json.update(local_json)

    print("Policy ID updated in JSON successfully. Updating policy on Databricks....")
    try:
        if args.DRY_RUN == "false":
            subprocess.check_call(
                [
                    "databricks",
                    "cluster-policies",
                    "edit",
                    "--json",
                    json.dumps(cluster_policy_json),
                ]
            )
        else:
            print("DRY RUN DETECTED, not actually updating policy")
    except Exception as e:
        print(str(e))
        sys.exit(1)

def add_group_to_cluster_policy(teams: list, cluster_id: str) -> None:
    """
    This method uses the Databricks API to add the teams/users to permissions as 'CAN USE'
    Args:
        teams (list): list of teams
        cluster_id (str): Cluster policy id to update
    Returns:
        None
    """

    # Modify args.DBX_INSTANCE for url
    instance = args.DBX_INSTANCE.rstrip('/')

    # check if the args.DBX_INSTANCE starts with 'https://' and build the URL accordingly
    url = f"https://{instance}/api/2.0/permissions/cluster-policies/{cluster_id}"
    if instance.startswith("https://"):
        url = f"{instance}/api/2.0/permissions/cluster-policies/{cluster_id}"

    # create the access list with the right format
    access_list = [{'user_name' if '@' in team else 'group_name': team, 'permission_level': 'CAN_USE'} for team in teams]
    
    # set the request headers
    headers = {
        'Authorization': f'Bearer {args.DBX_ACCESS_TOKEN}',
        'Content-Type': 'application/json'
    }
    # send the PATCH request to add the teams to the cluster policy
    response = requests.patch(url, headers=headers, data=json.dumps({"access_control_list": access_list}))

    try:
        # Try to parse the response as JSON
        response_json = response.json()

        # Check if the response JSON contains an error code
        if "error_code" in response_json:
            # If it does, print the error code
            print(response_json['error_code'])
        else:
            # If it doesn't, print "SUCCESS"
            print("SUCCESS")
    except:
        # If there's an error parsing the response as JSON, print "ERROR"
        print("ERROR")
        print(response.text)


###----------Main Start-------------###

# Set Argument Variables
parser = argparse.ArgumentParser()
parser.add_argument("DBX_INSTANCE")
parser.add_argument("DBX_ACCESS_TOKEN")
parser.add_argument("POLICY_DIR")
parser.add_argument("DRY_RUN")
parser.add_argument("CAN_USE")
args = parser.parse_args()
# Split CAN_USE into a list
args.CAN_USE = [s.strip() for s in args.CAN_USE.split(",")]

# Validate variable values
print("Validating Input Parameters...")
if args.DRY_RUN != "true" and args.DRY_RUN != "false":
    sys.exit('ERROR: Dry run variable must be set to "true" or "false".')
print("SUCCESS")
# Validate files exist in policy_dir
print("Validating scripts exists in provided directory: " + args.POLICY_DIR)

if not os.path.isdir(args.POLICY_DIR):
    sys.exit("ERROR: " + args.POLICY_DIR + " does not exist!")

if len(os.listdir(args.POLICY_DIR)) == 0:
    sys.exit("ERROR: " + args.POLICY_DIR + " does not contain any files!")
print("SUCCESS")

print("Configuring Databricks CLI....")
auth_filename = "auth"
authenticate_databricks_cli(auth_filename)
print("SUCCESS")

print("Verifying files in " + args.POLICY_DIR)
policy_files = os.listdir(args.POLICY_DIR)
for file in policy_files:
    if not file.endswith(".json"):
        sys.exit(
            "ERROR: " + file + " must be a JSON file. Please fix file and try again."
        )
print("SUCCESS")

for policy in policy_files:
    policy_full_path = args.POLICY_DIR + "/" + policy
    print("Generating JSON to match what CLI expects")
    generated_json = build_json_for_cli(policy_full_path)
    print("Checking if cluster policy exists already")
    policy_id = get_policy_id(generated_json["name"])
    if policy_id == "":
        print("New Cluster Policy detected. Adding new Policy to Databricks.")
        upload_new_cluster_policy(generated_json)
        print("SUCCESS")
    else:
        print("Updating existing policy on Databricks.")
        update_existing_cluster_policy(policy_id, generated_json)
        print("SUCCESS")
    if args.CAN_USE:
        policy_id = get_policy_id(generated_json["name"])
        print("Updating Permissions in Policy.")
        add_group_to_cluster_policy(args.CAN_USE, policy_id)

print("DONE")
