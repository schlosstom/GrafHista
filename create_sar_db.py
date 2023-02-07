#! /usr/bin/python
# ------------------------------------------------------------------------------
# Copyright (c) 2023 SUSE LLC
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of version 3 of the GNU General Public License as published by the
# Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, contact SUSE Linux GmbH.
#
# ------------------------------------------------------------------------------
# Author: Thomas Schlosser <thomas.schlosser@suse.com>
# 
# create_sar_db
#
# Imports data of a sar binary file and creates a mysql db. The mysql db can then
# be included into a Grafana dashboard for creating further queries and metrics.
#
# Changelog:    2023-01-30  v0.1    First testing.
#               2023-02-01  v0.11   Each sar file has it own DB based on it name.

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
def get_date_time(number):
    path = table_dict[number]['timestamp']  
    date_time = path['date'] + " " + path['time'] 
    return (date_time)


# Where to find the data
def get_data_and_path(number):
    path = table_dict[number]
    data_name = ""

    for key_name in (list(path.keys())):
        if key_name != 'timestamp':
            data_name = key_name

    if isinstance(path[data_name], dict):
        path = path[data_name]
    elif isinstance(path[data_name], list):
        path = path[data_name][0]
    else:
        print("An error occures. Exit") 
        sys.exit()   

    data_name = name_correction(data_name)

    return(data_name, path)    


# Create table string
def create_table_string():
    name, path = get_data_and_path(0)

    sql_string = "CREATE TABLE " + name + " (Date DATETIME"
    
    for key, value in path.items():
        key = name_correction(key)                        
        sql_string += ", " + key + data_type(value)

    sql_string += ")"
    print("    Table: " + name + " created")
    return(sql_string)


# Create insert string
def create_insert_string(number):
    date = get_date_time(number)
    name, path = get_data_and_path(number) 
    
    sql_string = "INSERT INTO " + name + " SET Date = \'" + date  + "\'"

    for key, value in path.items():
        key = name_correction(key)
        sql_string += ", " + str(key) + " = \'" + str(value) + "\' "

    return(sql_string)



 #### Main ######################################

create_db(args.file)

for option in OPTIONS:
    table_dict = capture_data(args.file, option)

    # Create table
    sql = create_table_string()
    MY_CURSOR.execute(sql)

    # Insert data 
    i = 0
    z = 0
    for z in table_dict:
        sql = create_insert_string(i)
        MY_CURSOR.execute(sql)
        my_db.commit()
        i += 1
