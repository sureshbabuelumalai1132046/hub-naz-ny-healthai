
import argparse
import os

logger = LM.get_logger(__name__)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--dbx_instance_url", required=True, help="URL for the databricks instance")
    parser.add_argument("-t", "--dbx_token", required=True, help="Personal access token for the databricks instance")
    parser.add_argument("-j", "--job_ids", required=True, help="Comma seperated string of job ids to run")

    args = parser.parse_args()

    db_conn = Databricks(args.dbx_instance_url, args.dbx_token)

    job_ids = args.job_ids.strip().split(',')

    job_to_run_ids = {}
    
    for job_id in job_ids:
        try:
            run_id = str(db_conn.run_job(int(job_id.strip())))
            logger.info(f"Job {job_id} running with run_id {run_id}")
        except Exception as e:
            logger.warning(f"Ran into an error {e} running job {job_id}")
            run_id = 'Failed'
        
        job_to_run_ids[job_id] = run_id

    with open(os.environ["GITHUB_OUTPUT"], 'a') as github_output:
        job_run_id_mapping_string = ', '.join([f"{job_id}:{run_id}" for job_id, run_id in job_to_run_ids.items()])
        print(f"run_ids={job_run_id_mapping_string}", file=github_output)
