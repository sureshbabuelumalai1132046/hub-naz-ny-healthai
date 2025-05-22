#!/usr/local/bin/python

import argparse
import sys
import os

logger = LM.get_logger(__name__)


if __name__ == "__main__":
    # read in arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--databricks_host", required=True, help="URL for the databricks instance")
    parser.add_argument(
        "-t", "--databricks_access_token", required=True, help="Personal access token for the databricks instance"
    )
    parser.add_argument("-u", "--repository_url", required=True, help="Repository URL (GitHub)")
    parser.add_argument(
        "-p",
        "--repository_path",
        required=True,
        help="Path at which to create the repository",
    )
    args = parser.parse_args()

    try:
        # create connection to databricks and call reusable methods
        dbx = Databricks(host=args.databricks_host, token=args.databricks_access_token, api_version="2.0")
        resp = dbx.create_repo(repository_url=args.repository_url, repository_path=args.repository_path)
        # create environment variable repo_id to pass to the update and delete methods
        repo_id = resp["id"]
        with open(os.environ["GITHUB_OUTPUT"], "a") as github_output:
            print(f"repo_id={repo_id}", file=github_output)
    except Exception as e:
        # write out error and exit workflow
        logger.error(e)
        sys.exit(1)
