
import argparse
import json
import os

logger = LM.get_logger(__name__)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--dbx_instance_url", required=True, help="URL for the databricks instance")
    parser.add_argument("-t", "--dbx_token", required=True, help="Personal access token for the databricks instance")
    parser.add_argument("-j", "--job_configs", required=True, help="Space seperated string of config file paths")
    parser.add_argument("-e", "--env", nargs="?", default="", help="Target environment mapped in the config file")
    parser.add_argument("--dry_run", action='store_true', help="To run as normal without deploying, required for action testing")
    
    args = parser.parse_args()

    db_conn = Databricks(args.dbx_instance_url, args.dbx_token)
    
    for job_config_path in args.job_configs.strip().split(' '):
        logger.info(f"Deleting job in {job_config_path}")
        with open(job_config_path, 'r') as job_config_info:
            job_config = json.loads(job_config_info.read())
        job_name = job_config['name']
        try:
            db_conn.delete_job(job_name = job_name)
        except KeyError:
            logger.warning(f"job name: {job_name} does not exist")
        except Exception as e:
            logger.error(e)
            raise e



