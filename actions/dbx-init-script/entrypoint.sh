#!/bin/sh -l

###----------SETUP-------------###

# Set Variables
SCRIPT_DIR=$3
GLOBAL=$4
DRY_RUN=$5
DBX_ACCESS_TOKEN=$2
DBX_INSTANCE=$1
TARGET_DBFS_ROOT_PATH=dbfs:/devops/init-scripts

# Exit on errors
set -e

# Create Authnetication
echo $DBX_ACCESS_TOKEN > auth
databricks configure -f auth --host $DBX_INSTANCE
rm auth


###---------VALIDATION----------###
echo "Validating variables..."
# Validate variable values
if [ $GLOBAL != "true" ] && [ $GLOBAL != "false" ] ; then
    echo "ERROR: Global variable must be set to \"true\" or \"false\" explicitly!!"
    exit 1
fi

if [ $DRY_RUN != "true" ] && [ $DRY_RUN != "false" ] ; then
    echo "ERROR: Dry run variable must be set to \"true\" or \"false\" explicitly!!"
    exit 1
fi
echo "SUCCESS"

# Validate files exist in script_dir
echo "Validating scripts exists in provided directory $SCRIPT_DIR...."
if [ ! -d $SCRIPT_DIR ] ; then
    echo "ERROR: $SCRIPT_DIR does not exist!"
    exit 1
elif [ -z "$(ls -A $SCRIPT_DIR)" ] ; then
    echo "ERROR: $SCRIPT_DIR does not contain any files!"
    exit 1
fi
echo "SUCCESS"

# Remove trailing slash if it exists (Credit: https://gist.github.com/luciomartinez/c322327605d40f86ee0c)
length=${#SCRIPT_DIR}
last_char=${SCRIPT_DIR:length-1:1}
[[ $last_char == "/" ]] && SCRIPT_DIR=${SCRIPT_DIR:0:length-1};

length=${#DBX_INSTANCE}
last_char=${DBX_INSTANCE:length-1:1}
[[ $last_char == "/" ]] && DBX_INSTANCE=${DBX_INSTANCE:0:length-1};

###---------EXECUTION----------###

# get the list of files
file_list=$(ls -A $SCRIPT_DIR)
for file in $file_list ; do
    echo "Found File: $file"
done

for file in $file_list ; do
    if [ $GLOBAL == "true" ] ; then
        echo "Adding $file to $DBX_INSTANCE Global Init Scripts"

        # check to see if script already exists
        file_script_id=$(curl -sS -H "Accept: application/json" \
            -H "Authorization: Bearer $DBX_ACCESS_TOKEN" \
            $DBX_INSTANCE/api/2.0/global-init-scripts | \
            jq -r --arg script_name "$file" '.scripts[]? | select (.name == $script_name) | .script_id')
        if [ $file_script_id ] ; then
            echo "$file init script already exists, updating current $file. "

            if [ $DRY_RUN == "false" ] ; then
                curl -sS -H "Accept: application/json" \
                    -H "Authorization: Bearer $DBX_ACCESS_TOKEN" \
                    -H 'Content-Type: application/json' \
                    --request PATCH \
                    --data "{\"name\":\"$file\", \"script\":\"$(cat $SCRIPT_DIR/$file | base64 -w 0)\"}" \
                    $DBX_INSTANCE/api/2.0/global-init-scripts/$file_script_id
                echo "Sucessfully updated $file in Global Init Scripts"
            else
                echo "DRY RUN DETECTED, NOT UPDATING $file"
            fi
            scripts_added="$scripts_added Updated $file in Global Init Scripts. "
        else
            echo "$file init script does not exist, adding $file"

            if [ $DRY_RUN == "false" ] ; then
                curl -sS -H "Accept: application/json" \
                    -H "Authorization: Bearer $DBX_ACCESS_TOKEN" \
                    --request POST \
                    --data "{\"name\":\"$file\", \"script\":\"$(cat $SCRIPT_DIR/$file | base64 -w 0)\", \"enabled\":\"true\"}" \
                    $DBX_INSTANCE/api/2.0/global-init-scripts
                echo "Sucessfully added $file to Global Init Scripts"
            else
                echo "DRY RUN DETECTED. NOT ADDING $file"
            fi
            scripts_added="$scripts_added Added $file to Global Init Scripts. "
        fi    
    else
        echo "ERROR: Adding init-scripts to DBFS root is not supported. Please use cluster-scoped init scripts from Workspace instead."
        exit 1
    fi
done


echo "init-script-path=$scripts_added" >> $GITHUB_OUTPUT
