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

Changelog:  2023-01-30  v0.1    First testing.
            2023-02-01  v0.11   Each sar file has it own DB based on it name.
            2023-02-07  v0.2    Code improvements
            2023-02-14  v0.4    Split python code
            2023-02-16  v0.6    Include the script in the container   

TODO:       * Improve error handling
            * Add a function to restart if there is a file/dir change outside (inotify??)
            * Handle duplicate sar files (e.g. same file in fullsysteminfodump and supportconfig)

"""

import sar_db
import subprocess
import json
import sys 
from pathlib import Path
import glob
import pymysql
from datetime import datetime


db_connect = pymysql.connect(
    host='mysql',
    port=3306,
    user='root',
    passwd='Suse1234',
    db='db'
)
MY_CURSOR = db_connect.cursor()
   

##### Constants #################################

# Options for the different sar types like CPU, memory, paging, swap,...
# see "man sar" for details 
OPTIONS = {'-u', '-r', '-B', '-W', '-v', '-q', '-S'}  



#### Functions ##################################

def capture_data(file, option):
    """ 
    Capture data of the sar file and store it to a dict. 
    The variable "option" is one of the sar option defind as global constant list (OPTIONS)
    The result is the "key address" where the needed data is starting.
    """
    try:
        dict = json.loads(subprocess.check_output(['sadf', '-j', file, '--', option], encoding='UTF-8'))
        path = dict['sysstat']['hosts'][0]      
    except:
        print("File not found")
        sys.exit(1)

    return(path)



def create_db(file):
    """ Create DATABSE based on the sar file name """
    try:
        # We also might need the hostname 
        hostname = capture_data(file, "-r")['nodename']

        database_name = hostname + "_" + Path(file).name
        sql = "DROP DATABASE IF EXISTS " + database_name
        MY_CURSOR.execute(sql)

        sql = "create database " + database_name
        MY_CURSOR.execute(sql)

        sql = "use " + database_name
        MY_CURSOR.execute(sql)   
        print(database_name, end=' [ ')
    except:
        print ("Error: ")   
        sys.exit(1) 



def create_tables(file, options):
    """ Main function for creating the database and all tables based on the given sar file """
    for option in options:
        table_dict = capture_data(file, option)['statistics']

        # Create table
        sql = sar_db.create_table_string(table_dict[0])
        MY_CURSOR.execute(sql)

        # Insert data 
        for data_set in table_dict:
            sql = sar_db.create_insert_string(data_set)
            MY_CURSOR.execute(sql)          
        db_connect.commit()

 
if __name__ == "__main__":

    sar_path = ('/var/log/sc/sar/', '/var/log/fu/var/log/sa/') 
    
    for path in sar_path:
        try:
            sar_files = glob.glob(path + "sa????????")
            for file in sar_files:                
                print(datetime.now(), file, end=' ')
                create_db(file)
                create_tables(file,OPTIONS)
                print(']')    
        except: 
            print("Error: An error occured collecting sar files!")
            #continue
  