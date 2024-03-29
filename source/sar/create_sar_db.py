#! /usr/bin/python3

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

Logs are written to: /var/log/sar_db.log
(inside the container grafhista)


Changelog:  2023-01-30  v0.1    First testing.
            2023-02-01  v0.11   Each sar file has it own DB based on it name.
            2023-02-07  v0.2    Code improvements
            2023-02-14  v0.4    Split python code
            2023-02-16  v0.6    Include the script in the container
            2023-02-24  v0.8    Add inotify function to trigger script on file change 
            2023-03-02  v0.9    - add config.yaml
                                - some error handling improvements (still not satisfied)
                                - promtail.yml improvements
            2023-04-05  v0.95   Changed the logic to be able capturing single dev and CPUs as well.
                                Some additional improvements  
            2023-04-24  v0.96   Add network devices                                                   

"""

import sar_db
import pymysql
import subprocess
import json
import sys 
from pathlib import Path
import glob
from datetime import datetime
import inotify.adapters
import logging

import yaml
import pprint

log_file = '/logs/create_sar_db.log'

subprocess.run(["rm", log_file])

logging.basicConfig(level=logging.INFO, filename=log_file, filemode='w',
                    format='%(asctime)s - %(levelname)s - %(message)s')


try:
    logging.info('Reading config file...')
    with open('config.yaml', 'r') as f: 
        config = yaml.safe_load(f)

except Exception as err:
    logging.error('Error reading config.yaml')
    exit(1)


db_connect = pymysql.connect(
    host=config['mysql']['host'],
    port=config['mysql']['port'],
    user=config['mysql']['user'],
    passwd=config['mysql']['passwd'],
    db=config['mysql']['db']
)
MY_CURSOR = db_connect.cursor()


def capture_data(file, option):
    """
    Capture data of the sar file and store it to a dict.
    The variable "option" is one of the sar option defind as global constant list (OPTIONS)
    The result is the "key address" where the needed data is starting.
    """
    try:
        # Comment out here to see every report.
        # logging.info(f'capture_data() - Reading {file} with option {option}')
        commands = "sadf -j " + file + " -- " + option
        command = commands.split()
        dict = json.loads(subprocess.check_output( command,  encoding='UTF-8'))
        path = dict['sysstat']['hosts'][0]
    except:
        logging.error(f'capture_data() - File: {file} not found or invalide option: {option}')
        sys.exit(1)

    return(path)

def create_db(sar_file, path_name, hostname):
    """ Create DATABASE based on the sar file name """
    try:
        database_name = hostname + "_" + path_name + "_" + Path(sar_file).name
        sql = "DROP DATABASE IF EXISTS " + database_name
        MY_CURSOR.execute(sql)

        sql = "create database " + database_name
        MY_CURSOR.execute(sql)

        sql = "use " + database_name
        MY_CURSOR.execute(sql)
    except:
        logging.error(f'create_db() - Error creating or dropping database {sar_file} for hostname {hostname}')
        sys.exit(1)


def create_table(key_name, item):
    """ Create DATABASE table for a single item (e.g. dev, memory, ...)"""
    try:
        # Unfortunately swap and memory have the same key_name "memory"
        # If there is a data key swapfree we will remane the key_name to "swap"    
        if 'swpfree'  in item.keys():
            key_name = "swap"

        sql_string = "CREATE TABLE " + key_name + " (Date DATETIME"
        for key, value in item.items():
            sql_string += ", " + key + sar_db.data_type(value)
        sql_string += ")"
        sql = sar_db.name_correction(sql_string)
        
        MY_CURSOR.execute(sql)
    except:
        logging.error(f'create_table() - Error creating table {key_name} ')
        sys.exit(1)            



def insert_table(key_name, item, time_line):
    """ Insert data for a single item (e.g. dev, memory, ...)"""
    try:
        # Unfortunately swap and memory have the same key_name "memory"
        # If there is a data key swapfree we will remane the key_name to "swap"    
        if 'swpfree'  in item.keys():
            key_name = "swap"

        date = sar_db.get_date_time(time_line)
        sql_string = "INSERT INTO " + key_name + " SET Date = \'" + date  + "\'"
        for key, value in item.items():
            #key = sar_db.name_correction(key)
            sql_string += ", " + str(key) + " = \'" + str(value) + "\' "
        sql = sar_db.name_correction(sql_string)
        MY_CURSOR.execute(sql)
    except:
        logging.error(f'insert_table() - Error inserting {key_name} for date {date}')
        sys.exit(1)    



def prepare_tables(sar_file):
    """ Preparing the sar_file data for the tables  """
    try:
        # For each item/option (-r , -u, .option..)
        for option in config['options'].items():
            option_key, option_value = option
            dict_option = capture_data(sar_file,option_value)['statistics']
            create_table_flac  = True

            # For every timeline (e.g. '2023-02-06 07:18:02')
            for time_line in dict_option:                
                key_name = (set(time_line.keys()) - {'timestamp'}).pop()

                # The network "offset" is more encapsulated like the other. For the moment I handle 
                # it as a special case. TODO: have a more generic solution for all different possibilities.
                # Below is a example of one time line:
                # "timestamp": {
                # "network": {
                #               "net-dev": [
			    #                           {"iface": lo ...
                #                           {"iface": eth0 ...
                #                              ...
                #                          ]
                #             }
                if option_key == 'network':
                    key_name02 = (set(time_line[key_name].keys()) - {'network'}).pop()
                    item = time_line[key_name][key_name02][0]

                    # Make sure the table will be created only once
                    if create_table_flac:
                        create_table(option_key, item)
                        create_table_flac  = False                    
  
                    # Insert data for the created table    
                    for item in time_line[key_name][key_name02]:
                        insert_table(option_key, item, time_line)


                # Most items has only one "device" like CPU(ALL) or memory, etc.
                # This can be seen by the type which is in that case a dictionary part.
                # Below is a example of one time line:                
                # "timestamp": {
                # "memory": {"memfree":
                #
                elif isinstance(time_line[key_name], dict):

                    # There is only one row for this time_line
                    item = time_line[key_name]

                    # Make sure the table will be created only once
                    if create_table_flac:
                        create_table(key_name, item)
                        create_table_flac  = False

                    # Insert data for the created table    
                    insert_table(key_name, item, time_line)

                # Some items like DEV's or (single) CPU's have more items based on one timeline
                # This can be seen by the type list. In this case an additional for loop is needed.
                # Below is a example of one time line:                
                # "timestamp": {                    
                #  "cpu-load": [
                #                 {"cpu": "all", "user": ...
                #                 {"cpu": "0", "user": ...               
                #                  ...
                #              ]
                #             
                elif isinstance(time_line[key_name], list):

                    # The first list item contains a list of rows
                    item = time_line[key_name][0]

                    # Make sure the table will be created only once. 
                    if create_table_flac:    
                        create_table(key_name, item)
                        create_table_flac  = False

                    # Insert data for the created table    
                    for item in time_line[key_name]:
                        insert_table(key_name, item, time_line)

        db_connect.commit()
    except:
        logging.error(f'prepare_tables() - Error on preparing tables Option: {option} Keyname: {key_name} ')
        sys.exit(1)        


def load_data():
    """ Main process for loading all available sar files"""
    logging.info('load_data() - Starting... ')

    # For each path written in config file.
    for path_name, path_value in config['sar_path'].items():
        sar_path = glob.glob(path_value + "sa????????")

        # For each sar file in given path.
        for sar_file in sar_path:
            host_name = capture_data(sar_file, " ")['nodename']
            create_db(sar_file, path_name, host_name)
            logging.info(f'load_data() - Scanning sar file: {sar_file}')
            prepare_tables(sar_file)

def main():
    """ Triggers the function load_data() if there are any changes in logs/ folder"""
    # First run on startup
    load_data()
    logging.info('main() - Initial loop done - waiting for first changes!')
    
    # monitor the /logs folder inside the container 
    i = inotify.adapters.InotifyTree('/logs')

    for event in i.event_gen(yield_nones=False):
        (_, type_names, _, _) = event

        # Triggers the main function load_data() by any new or deleted files or folders 
        if 'IN_CREATE' in type_names or 'IN_DELETE' in type_names:
            logging.info('main() - Changes in folder detected')
            load_data()
            logging.info('main() - Waiting for new changes!')



if __name__ == "__main__":
    main()
