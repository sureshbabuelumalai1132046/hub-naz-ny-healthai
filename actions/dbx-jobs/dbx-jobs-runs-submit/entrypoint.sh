#!/bin/sh

pip --no-cache-dir install -q DBUtils
python /dbx-submit-onetime-job.py -j $1 -d $2 -t $3 -e "$4" -p "$5" -n "$6" -c "$7"
