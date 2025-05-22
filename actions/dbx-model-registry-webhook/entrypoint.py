#!/usr/local/bin/python

import os
import json
import sys
import requests
import random
import string


def validate_local_webhook_json(webhook_path: str):
    """
    This method validates a provided JSON file to make sure it meets the custom webhook schema
    Args:
        webhook_path (str): path to JSON file
    """
    with open(webhook_path, "r+") as local_webhook_json_file:
        webhook_definition = json.load(local_webhook_json_file)
        print("Checking json schema for " + os.path.basename(webhook_path))
        if "events" not in webhook_definition:
            sys.exit("ERROR: Missing events from json schema.")
        elif "caller_url" not in webhook_definition:
            sys.exit("ERROR: Missing caller_url from json schema.")
        elif "caller_auth_type" not in webhook_definition:
            sys.exit("ERROR: Missing caller_auth_type from json schema.")

        if webhook_definition["caller_auth_type"].strip().lower() != "bearer":
            sys.exit('ERROR: The only caller_auth_type supported is "bearer".')


def generate_mlflow_api_json_from_local_json(
    webhook_path: str, caller_auth_string: str
) -> dict:
    """
    This method builds a proper MLFlow API JSON schema from the custom webhook schema that can be used with the MLFlow API to create a Databricks Model Registry webhook.
    Args:
        webhook_path (str): Path to custom webhook JSON file
        caller_auth_string (str): The authentication string used to authenticate the caller_url when triggered
    Returns:
        dict: Json Dict representation of a proper MLFlow JSON schema
    """
    with open(webhook_path, "r+") as local_webhook_json_file:
        local_webhook_definition = json.load(local_webhook_json_file)
        # Handle optional json objects
        mlflow_proper_definition = {}
        if "model_name" in local_webhook_definition:  # TODO: clean up if statement
            if local_webhook_definition["model_name"].strip() == "":
                print(
                    "WARNING: model_name detected but is blank. Please add a model name or remove object."
                )
            else:
                mlflow_proper_json["model_name"] = local_webhook_definition[
                    "model_name"
                ]

        if "description" not in local_webhook_definition:
            mlflow_proper_definition[
                "description"
            ] = "auto-generated description from a GitHub Action"
        # Add the assumed json objects
        mlflow_proper_definition["status"] = "ACTIVE"
        events_array = local_webhook_definition["events"].split(",")
        mlflow_proper_definition["events"] = events_array
        # Build the http_utl_spec
        http_url_spec = {}
        http_url_spec["url"] = local_webhook_definition["caller_url"]
        http_url_spec["secret"] = "".join(random.choices(string.ascii_lowercase, k=10))
        if local_webhook_definition["caller_auth_type"].strip().lower() == "bearer":
            http_url_spec["authorization"] = "Bearer " + caller_auth_string

        mlflow_proper_definition["http_url_spec"] = http_url_spec
        return mlflow_proper_definition


def create_model_registry_webhook(
    webhook_json: dict, dbx_instance: str, dbx_token: str
) -> str:
    """
    This method creates a Databricks Model Registry webhook in the provided Databricks Instance using the MLFlow API.
    Args:
        webhook_json (dict): The JSON definition used to create the webhook
        dbx_instance (str): The url for the Databricks Instance
        dbx_token (str): The personal access token used to authenticate against the Databricks Instance
    Returns:
        dict: Json Dict representation of cluster policy based on file path
    """
    # Databricks API URL (strip trailing slash if it exists)
    url = dbx_instance.rstrip("/") + "/api/2.0/mlflow/registry-webhooks/create"
    # Databricks API Headers
    headers = {
        "Authorization": "Bearer " + dbx_token,
        "Content-Type": "text/plain",
    }
    json_body = json.dumps(webhook_json).encode("utf-8")
    if DRY_RUN == "true":
        print("DRY RUN DETECTED, not actually creating webhook")
        return "none"
    else:
        try:
            resp = requests.post(url, headers=headers, data=json_body)
            jsonResponse = resp.json()
            resp.raise_for_status()
        except Exception as e:
            print(str(e))
            sys.exit(1)
        return jsonResponse["webhook"]["id"]


###----------Main Start-------------###

# Set Argument Variables
DBX_INSTANCE = sys.argv[1]
DBX_ACCESS_TOKEN = sys.argv[2]
WEBHOOKS_DIR = sys.argv[3]
CALLER_AUTH_STRING = sys.argv[4]
DRY_RUN = sys.argv[5].lower()

# Validate variable values
print("Validating Input Parameters...")
if DRY_RUN != "true" and DRY_RUN != "false":
    sys.exit('ERROR: Dry run variable must be set to "true" or "false".')
print("SUCCESS")
# Validate files exist in webhooks_dir
print("Validating scripts exists in provided directory: " + WEBHOOKS_DIR)

if not os.path.isdir(WEBHOOKS_DIR):
    sys.exit("ERROR: " + WEBHOOKS_DIR + " does not exist!")

if len(os.listdir(WEBHOOKS_DIR)) == 0:
    sys.exit("ERROR: " + WEBHOOKS_DIR + " does not contain any files!")
print("SUCCESS")

print("Verifying files in " + WEBHOOKS_DIR)
webhook_files = os.listdir(WEBHOOKS_DIR)
for file in webhook_files:
    if not file.endswith(".json"):
        sys.exit(
            "ERROR: " + file + " must be a JSON file. Please fix file and try again."
        )
    file_full_path = WEBHOOKS_DIR + "/" + file
    validate_local_webhook_json(file_full_path)
print("SUCCESS")


# Create the webhooks
webhooks = []
try:
    for webhook in webhook_files:
        webhook_full_path = WEBHOOKS_DIR + "/" + webhook
        print("Creating MLFlow proper API JSON from " + webhook_full_path)
        mlflow_proper_json = generate_mlflow_api_json_from_local_json(
            webhook_full_path, CALLER_AUTH_STRING
        )
        print("SUCCESS")
        print("Creating webhook in provided DBX instance for " + webhook_full_path)
        webhook_id = create_model_registry_webhook(
            mlflow_proper_json, DBX_INSTANCE, DBX_ACCESS_TOKEN
        )
        webhooks.append(webhook_id)
        print("Created webhook: " + webhook_id)  # Load this into the array
except Exception as e:
    print(str(e))
    sys.exit(1)

with open(os.environ['GITHUB_OUTPUT'], "a") as github_output:
    print(f"webhooks-created={','.join(webhooks)}", file=github_output)

print("DONE")
