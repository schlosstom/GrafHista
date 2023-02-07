#! /usr/bin/python

"""
------------------------------------------------------------------------------
Copyright (c) 2023 SUSE LLC

This program is free software; you can redistribute it and/or modify it under
the terms of version 3 of the GNU General Public License as published by the
Free Software Foundation.

This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program; if not, contact SUSE Linux GmbH.
 
------------------------------------------------------------------------------
Author: Thomas Schlosser <thomas.schlosser@suse.com>
 
create_sar_db.py

Imports data of a sar binary file and creates a mysql db. The mysql db can then
be included into a Grafana dashboard for creating further queries and metrics.

Changelog:    2023-01-30  v0.1    First testing.
              2023-02-01  v0.11   Each sar file has it own DB based on it name.
              2023-02-07  v0.2    Code improvements
"""


import subprocess
import mysql.connector
import argparse
import json
import sys 
from pathlib import Path


# Handle arguments 
# A sar binary file is needed as argument
# Make sure to have the sadf tool installed
parser = argparse.ArgumentParser()
parser.add_argument('-f', '--file', dest='file', type=str, help='sar binary file to load into the database!')
parser.add_argument('-d', '--dir', dest='dir', type=str, help='Directory whre all the sa.* files can be found')
args = parser.parse_args()


# Prepare mysql 
my_db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Suse1234",
)

##### Constants #################################

# For operation.
MY_CURSOR = my_db.cursor()

# Options for the different sar types like CPU, memory, paging, swap,...
# see "man sar" for details 
OPTIONS = {'-u', '-r', '-B', '-W', '-v', '-q'}  



#### Functions ##################################

# Create db based on the sar file name
def create_db(file):

    database_name = Path(file).name
    sql = "DROP DATABASE IF EXISTS " + database_name
    MY_CURSOR.execute(sql)

    sql = "create database " + database_name
    MY_CURSOR.execute(sql)

    sql = "use " + database_name
    MY_CURSOR.execute(sql)
    
    print("Database: " + database_name + " created")


# Capture all data of the sar file and store it to a dict
def capture_data(file, option):
    dict = json.loads(subprocess.check_output(['sadf', '-j', file, '--', option], encoding='UTF-8'))
    path = dict['sysstat']['hosts'][0]['statistics']
    return(path)


# Select mysql data type
def data_type(value):
    if isinstance(value, float):          
        return(" FLOAT(32,2)")
    elif isinstance(value, str):
        return(" VARCHAR(255)")
    elif isinstance(value, int):
        return(" BIGINT")


# Correct naming problems 
def name_correction(name):
    if '-' in name:
        name = name.replace('-','_')

    if name == 'system':
            name += '_'

    return(name)


# Where to find the time
def get_date_time(data_set):
    path = data_set['timestamp']  
    date_time = path['date'] + " " + path['time'] 
    return (date_time)


# Where to find the data
def get_data_and_path(data_set):

    key_name = (set(data_set.keys()) - {'timestamp'}).pop()

    if isinstance(data_set[key_name], dict):
        value = data_set[key_name]
    elif isinstance(data_set[key_name], list):
        value = data_set[key_name][0]
    else:
        print("An error occures. Exit") 
        sys.exit(1)   

    return name_correction(key_name), value


# Create table string
def create_table_string(data_set):
    name, path = get_data_and_path(data_set)

    sql_string = "CREATE TABLE " + name + " (Date DATETIME"
    
    for key, value in path.items():
        key = name_correction(key)                        
        sql_string += ", " + key + data_type(value)

    sql_string += ")"
    print("    Table: " + name + " created")
    return(sql_string)


# Create insert string
def create_insert_string(data_set):
    date = get_date_time(data_set)
    name, path = get_data_and_path(data_set) 
    
    sql_string = "INSERT INTO " + name + " SET Date = \'" + date  + "\'"

    for key, value in path.items():
        key = name_correction(key)
        sql_string += ", " + str(key) + " = \'" + str(value) + "\' "

    return(sql_string)


def create_tables(file, options):
    for option in options:
        table_dict = capture_data(file, option)

        # Create table
        sql = create_table_string(table_dict[0])
        MY_CURSOR.execute(sql)

        # Insert data 
        for data_set in table_dict:
            sql = create_insert_string(data_set)
            MY_CURSOR.execute(sql)          
        my_db.commit()


 #### Main ######################################

create_db(args.file)
create_tables(args.file,OPTIONS)



