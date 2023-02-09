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
from mysql.connector import errorcode
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
try:
    my_db = mysql.connector.connect(
        host="localhost",
        user="root",
        password="Suse1234",
    )
    MY_CURSOR = my_db.cursor()
except mysql.connector.Error as err: 
    print( "Error: ", err.errno, err.msg)
    sys.exit(1)



##### Constants #################################

# Options for the different sar types like CPU, memory, paging, swap,...
# see "man sar" for details 
OPTIONS = {'-u', '-r', '-B', '-W', '-v', '-q', '-S'}  



#### Functions ##################################


def create_db(file):
    """ Create DATABSE based on the sar file name """
    try:

        database_name = Path(file).name
        sql = "DROP DATABASE IF EXISTS " + database_name
        MY_CURSOR.execute(sql)

        sql = "create database " + database_name
        MY_CURSOR.execute(sql)

        sql = "use " + database_name
        MY_CURSOR.execute(sql)
    
        print("Database: " + database_name + " created")

    except mysql.connector.Error as err:
        print ("Error: ", err.errno, err.msg)   
        sys.exit(1) 



def capture_data(file, option):
    """ 
    Capture data of the sar file and store it to a dict. 
    The variable "option" is one of the sar option defind as global constant list (OPTIONS)
    The result is the "key address" where the needed data is starting.
    """
    try:
        dict = json.loads(subprocess.check_output(['sadf', '-j', file, '--', option], encoding='UTF-8'))
        path = dict['sysstat']['hosts'][0]['statistics']
    except:
        print("File not found")
        sys.exit(1)

    return(path)


def data_type(value):
    """ Returns mysql value type based on the value type we get from the dict."""
    if isinstance(value, float):          
        return(" FLOAT(32,2)")
    elif isinstance(value, str):
        return(" VARCHAR(255)")
    elif isinstance(value, int):
        return(" BIGINT")


def name_correction(name):
    """ Correct some not allowed names"""
    if '-' in name:
        name = name.replace('-','_')

    if name == 'system':
            name += '_'

    return(name)


def get_date_time(data_set):
    """ Returns date and time from the given index and combine it together"""
    path = data_set['timestamp']  
    date_time = path['date'] + " " + path['time'] 
    return (date_time)


def get_data_and_path(data_set):
    """ Returns the "key address and the name from the given index  """

    key_name = (set(data_set.keys()) - {'timestamp'}).pop()

    # Some data like cpu_load are stored in a single list element
    # We check for list and assume that there is only one list element [0].
    if isinstance(data_set[key_name], dict):
        value = data_set[key_name]
    elif isinstance(data_set[key_name], list):
        value = data_set[key_name][0]
    else:
        print("An error occures. Exit") 
        sys.exit(1)   

    # Unfortunately swap and memory have the keyname "memory"
    # If there is a data key swapfree we will remane the key_name to swap
    if 'swpfree'  in value.keys():
        key_name = "swap"

    return name_correction(key_name), value



def create_table_string(data_set):
    """ Returns the sql string for creating the table based on the given index """
    name, path = get_data_and_path(data_set)

    sql_string = "CREATE TABLE " + name + " (Date DATETIME"
    
    for key, value in path.items():
        key = name_correction(key)                        
        sql_string += ", " + key + data_type(value)

    sql_string += ")"
    print("    Table: " + name + " created")

    return(sql_string)


def create_insert_string(data_set):
    """ Returns the sql string for inserting proper data to the table based on the given index """
    date = get_date_time(data_set)
    name, path = get_data_and_path(data_set) 
    
    sql_string = "INSERT INTO " + name + " SET Date = \'" + date  + "\'"

    for key, value in path.items():
        key = name_correction(key)
        sql_string += ", " + str(key) + " = \'" + str(value) + "\' "

    return(sql_string)


def create_tables(file, options):
    """ Main function for creating the database and all tables based on the given sar file """
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



