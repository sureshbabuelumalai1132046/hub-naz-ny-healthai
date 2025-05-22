#!/usr/local/bin/python

import argparse
import json

logger = LM.get_logger(__name__)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-j", "--job_run_config_path", required=True, help="The path to the config file for the job")
    parser.add_argument("-d", "--dbx_instance_url", required=True, help="URL for the databricks instance")
    parser.add_argument("-t", "--dbx_token", required=True, help="Personal access token for the databricks instance")
    parser.add_argument("-e", "--env", nargs="?", default="", help="Target environment mapped in the config file")
    parser.add_argument(
        "-p", "--notebook_base_params", nargs="?", default="", help="Notebook base parameters for running the notebook"
    )
    parser.add_argument("-n", "--notebook_path", nargs="?", default="", help="Path to a Databricks notebook to run")
    parser.add_argument(
        "-c", "--poll_for_completion", nargs="?", default="true", help="Whether to poll for job completion"
    )

    args = parser.parse_args()

    logger.info("Starting one-time job run submission.")
    logger.info(f"DBX Instance URL: {args.dbx_instance_url}")
    logger.info(f"Job run config file: {args.job_run_config_path}")
    logger.info(f"Notebook base parameters: {args.notebook_base_params}")
    logger.info(f"Notebook path: {args.notebook_path}")
    logger.info(f"Poll for completion: {args.poll_for_completion}")

    with open(args.job_run_config_path, "r") as config_file:
        config_json = json.loads(config_file.read())

    if args.env != "":
        config_json = config_json[args.env]

    dbx_conn = Databricks(args.dbx_instance_url, args.dbx_token)
    # This action is designed for simple jobs that only have one task in the list of tasks.
    # Additional tasks would require a mapping between the tasks and parameters.
    if args.notebook_base_params != "" or args.notebook_path != "":
        dbx_conn.update_notebook_tasks(
            config_json["tasks"][0],
            {} if args.notebook_base_params == "" else json.loads(args.notebook_base_params),
            args.notebook_path,
        )

    job_id = dbx_conn.submit_onetime_run(config_json)
    if args.poll_for_completion.lower() == "true":
        logger.info(f"Polling for job completion. Job ID: {job_id}")
        resp = dbx_conn.poll_run_for_completion(job_id, wait_between_polls_sec=10)
        status, _ = dbx_conn.parse_job_run_state(resp)
        logger.info(f"Final job run status: {status}")
        assert status == "SUCCESS"
    else:
        logger.info(f"Job submitted. Job ID: {job_id}. Not polling for completion.")
