#!/bin/sh

echo "[global]
pip --no-cache-dir install -q DBUtils
python /dbx-create-repo.py -d $1 -t $2 -u $3 -p $4
