import argparse
import json
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s:%(levelname)s:%(process)d:%(name)s:%(module)s:%(lineno)d:%(message)s",
)

# Create a logger
logger = logging.getLogger(__name__)


def check_for_timeout(job_config: dict) -> None:
    """
    This method is used to check if a timeout is configured for the job. If not, it logs an error and exits.
    Args:
        job_config (dict): The job configuration dictionary.
    Raises:
        SystemExit: If the timeout is not configured.
    """
    # check that timeout_seconds is configured and is greater than 0
    # a value of zero in the Databricks jobs API means no timeout
    if job_config.get("timeout_seconds", 0) > 0:
        logger.info(
            f"Timeout set to {job_config['timeout_seconds']} seconds on job {job_config['name']}"
        )
    else:
        logger.error(
            f"Timeout is not configured on job {job_config['name']}. Please configure a timeout for the job by setting timeout_seconds to an integer larger than 0. A value of 0 means no timeout (0 is the default)."
        )
        exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-j", "--job-path", required=True, help="Path to the job JSON file."
    )

    args = parser.parse_args()

    # open job config file
    with open(args.job_path, "r") as file:
        job_config = json.load(file)

    # check for timeout
    check_for_timeout(job_config)