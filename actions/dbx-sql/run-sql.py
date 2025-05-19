"""
A script for running SQL on Databricks using the Databricks API.
"""
from databricks import sql
import argparse
import pandas as pd
import re

def split_sql_statements(script):
    """
    Split a SQL script into individual statements. This will strip comments out of the statements as well.

    :param script: A string containing one or more SQL statements.
    :return: A list of individual SQL statements.
    """
    statements = []      # initialize an empty list to hold the SQL statements
    statement = ""       # initialize an empty string to hold the current statement
    in_string = False    # initialize a boolean variable to track whether we're inside a string literal
    in_comment = False   # initialize a boolean variable to track whether we're inside a comment
    comment_start = None # initialize a variable to track the start index of the current comment
    
    # Loop over each character in the script string
    i = 0
    while i < len(script):
        c = script[i]
        # If we encounter a semicolon that's not inside a string or comment,
        # we've reached the end of a statement. Add the statement to the list
        # of statements and start building a new statement.
        if c == ";" and not in_string and not in_comment:
            statements.append(statement.strip())
            statement = ""
        elif c == "'" and (i == 0 or script[i-1] != "\\"):
            in_string = not in_string   # Toggle the in_string variable if we encounter a single-quote character
            statement += c
        elif c == "-" and i < len(script) - 1 and script[i+1] == "-":
            in_comment = True   # Set the in_comment variable to True if we encounter a double-dash sequence
            comment_start = i
        elif c == "/" and i < len(script) - 1 and script[i+1] == "*":
            in_comment = True   # Set the in_comment variable to True if we encounter a /* sequence
            comment_start = i
        elif c == "*" and i < len(script) - 1 and script[i+1] == "/":
            in_comment = False   # Set the in_comment variable to False if we encounter a */ sequence
            script = script[:comment_start] + script[i+2:]
            i = comment_start - 1
        elif c == "\n":
            if in_comment and comment_start is not None:
                script = script[:comment_start] + script[i+1:]
                i = comment_start - 1
            in_comment = False  # Reset the in_comment variable if we encounter a newline character
            statement += c
        elif not in_comment:
            statement += c  # Add the current character to the statement string
        i += 1
    
    # If there's still an unfinished statement at the end of the script, add it to the list of statements.
    if statement.strip():
        statements.append(statement.strip())
    
    return statements   # Return the list of individual SQL statements


def clean_dbx_hostname(hostname):
    """
    Clean the Databricks hostname by removing 'https://' prefix and everything after '.net'

    :param hostname: The Databricks hostname to be cleaned
    :return: The cleaned Databricks hostname
    """
    if hostname.startswith("https://"):
        hostname = hostname[8:]
    if ".net" in hostname:
        hostname = hostname.split(".net")[0] + ".net"
    return hostname

def run_sql_on_dbx(host,warehouse_id,access_token,script):
    """
    Connects to Databricks API and executes the SQL script on the specified Databricks SQL warehouse.

    :param host: The Databricks hostname to connect to.
    :param warehouse_id: The ID of the SQL Warehouse to execute SQL commands on.
    :param access_token: The Databricks access token.
    :param script: The SQL script to be executed.
    """
    connection = sql.connect(
    server_hostname=host,
    http_path=f"/sql/1.0/warehouses/{warehouse_id}",
    access_token=access_token)

    cursor = connection.cursor()

    # Split the script into individual statements and remove comments
    sql_statements = split_sql_statements(script)
    for statement in sql_statements:
        # If it is a create statement, check if the catalog name ends with _dev
        print(f"------CHECKING FOR CREATE STATEMENT-----\n")
        if statement.strip().upper().startswith(("CREATE")):
                match = re.search(r'\b\w+\.\w+\.\w+\b', statement)
                text_before_first_period = match.group().split('.')[0] 
                try:
                    if not text_before_first_period.lower().endswith('_dev'):  
                        print("ERROR: Only those tables, whose catalog names conclude with '_dev', from DEV Catalogs, are permitted in the CREATE statements")
                        exit(1)
                except AttributeError:
                    print(f"ERROR: The attempt is to create the object: {match} which is in a NON-DEV catalog. Please use a DEV catalog for CREATE statements")
                    exit(1)
        print(f"------RUNNING SQL STATMENT-----\n {statement}")
        if statement.strip().upper().startswith(("CREATE", "ALTER", "DROP", "TRUNCATE", "COMMENT", "DELETE", "UPDATE", "INSERT")):
            try:
                if not args.dry_run:
                    cursor.execute(statement)
                else:
                    print("DRY RUN DETECTED: NOT RUNNING STATEMENT ON DATABRICKS")
            except sql.Error as e:
                print('ERROR:', e.args[0])
                exit(1)
            else:
                print(f"{statement.strip().split(' ')[0].upper()} SUCCESS\n")
        elif statement.strip().upper().startswith(("EXPLAIN")):
            try:
                ls = cursor.execute(statement).fetchall()
                df = pd.DataFrame(ls, columns = ["plan"])
                output_message = ""
                for row in range(df["plan"].count()):
                    output_message = output_message + str(df["plan"].loc[row])
                if "error occurred during query planning" in output_message.lower():
                    print('ERROR:', output_message)
                    exit(1)
            except Exception as e:
                print(f"An unexpected error has occurred: {e}")
                exit(1)
            else:
                print("EXPLAIN successfully ran")
        else:
            print("ERROR: Statement type not supported")
            exit(1)

    cursor.close()
    connection.close()

## Main
parser = argparse.ArgumentParser(
                prog='Run SQL on Databricks',
                description='This script take an SQL file and runs it on provided Databricks SQL Warehouse')
parser.add_argument("-n", "--databricks-hostname", required=True, help="The Databricks Hostname to run SQL on")
parser.add_argument("-w", "--sql-warehouse-id", required=True, help="The Databricks SQL Warehouse HTTP path")
parser.add_argument("-t", "--databricks-token", required=True, help="Databricks Token for authentication")
parser.add_argument("-f", "--file-path", required=True, help="File path to SQL to be ran")
parser.add_argument("--dry-run", action='store_true', help="Initiate a dry run of the script. This will do everything except run the script on Databricks.")

args = parser.parse_args()

with open(args.file_path, 'r') as sql_file:
    script = sql_file.read()

# Clean the databricks hostname if needed
dbx_hostname = clean_dbx_hostname(args.databricks_hostname)

# Run the SQL script
run_sql_on_dbx(dbx_hostname,args.sql_warehouse_id,args.databricks_token,script)