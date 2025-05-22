import json
import subprocess
import argparse
import logging

if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Update cluster policies in a Databricks job JSON file."
    )
    parser.add_argument("--job-path", help="Path to the job JSON file.")
    parser.add_argument(
        "--fail-on-missing-policy",
        action="store_true",
        help="Fail if a cluster policy is not found.",
    )
    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s:%(levelname)s:%(process)d:%(name)s:%(module)s:%(lineno)d:%(message)s",
    )

    # Create a logger
    logger = logging.getLogger(__name__)

    # Load job JSON file
    with open(args.job_path) as f:
        job = json.load(f)

    # Get cluster policies from Databricks
    cluster_policies_output = subprocess.check_output(
        ["databricks", "cluster-policies", "list", "--output", "JSON"]
    )
    cluster_policies = json.loads(cluster_policies_output)["policies"]

    # Prepare a dictionary to map policy names to ids
    policy_dict = {p["name"]: p["policy_id"] for p in cluster_policies}

    # Log the cluster policies
    logger.info(f"Cluster Policies: {policy_dict}")

    # Iterate over each cluster in the job
    for cluster in job.get("job_clusters", []):
        if "new_cluster" in cluster and "policy_id" in cluster["new_cluster"]:
            cluster_policy_name = cluster["new_cluster"]["policy_id"]
            logger.info(
                f"Cluster policy being used in job config: {cluster_policy_name}"
            )
            if cluster_policy_name in policy_dict:
                logger.info(
                    f"Cluster policy {cluster_policy_name} Found! Updating to use ID: {policy_dict[cluster_policy_name]}"
                )
                cluster["new_cluster"]["policy_id"] = policy_dict[cluster_policy_name]
            elif args.fail_on_missing_policy:
                logger.error(
                    f"Did not find cluster policy. Assuming ID is defined in job json or not using a cluster policy. fail_on_missing_policy = {args.fail_on_missing_policy}, exiting..."
                )
                exit(1)
            else:
                logger.warning(
                    f"Did not find cluster policy. Assuming ID is defined in job json or not using a cluster policy. fail_on_missing_policy = {args.fail_on_missing_policy}, continuing..."
                )

    # Save the updated job back to the JSON file
    with open(args.job_path, "w") as f:
        json.dump(job, f)