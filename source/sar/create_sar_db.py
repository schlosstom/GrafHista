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

Changelog:  2023-01-30  v0.1    First testing.
            2023-02-01  v0.11   Each sar file has it own DB based on it name.
            2023-02-07  v0.2    Code improvements
            2023-02-14  v0.4    Split python code
            2023-02-16  v0.6    Include the script in the container
            2023-02-24  v0.8    Add inotify function to trigger script on file change 

TODO:       * Improve error handling

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


logging.basicConfig(level=logging.INFO, filename='/var/log/sar_db.log', filemode='w',
                    format='%(asctime)s - %(levelname)s - %(message)s')


db_connect = pymysql.connect(
    host='mysql',
    port=3306,
    user='root',
    passwd='Suse1234',
    db='db'
)
MY_CURSOR = db_connect.cursor()


OPTIONS = {'-u', '-r', '-B', '-W', '-v', '-q', '-S'}
"""
Options for the different sar types like CPU, memory, paging, swap,...
see "man sar" for details 
"""



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
        logging.error(f'capture_data() - File: {file} not found or invalide option: {option}')
        sys.exit(1)

    return(path)



def create_db(file):
    """ Create DATABSE based on the sar file name """
    try:
        # We need the hostname 
        hostname = capture_data(file, "-r")['nodename']

        database_name = hostname + "_" + Path(file).name
        sql = "DROP DATABASE IF EXISTS " + database_name
        MY_CURSOR.execute(sql)

        sql = "create database " + database_name
        MY_CURSOR.execute(sql)

        sql = "use " + database_name
        MY_CURSOR.execute(sql)
        logging.info(f'create_db() - Create database: {database_name}')
    except:
        logging.error(f'create_db() - Error creating or dropping database {file} for hostname {hostname}')
        sys.exit(1)



def create_tables(file, options):
    """ Main function for creating the database and all tables based on the given sar file """
    for option in options:
        table_dict = capture_data(file, option)['statistics']

        # Create table
        sql = sar_db.create_table_string(table_dict[0])
        logging.debug(f'create_tables() - create SQL string is: {sql}')
        MY_CURSOR.execute(sql)

        # Insert data
        for data_set in table_dict:
            sql = sar_db.create_insert_string(data_set)
            logging.debug(f'create_tables() - Insert SQL is is: {sql}')
            MY_CURSOR.execute(sql)

        db_connect.commit()


def load_data():
    """ Main process for loading all available sar files"""
    logging.info('load_data() - Starting load_loop()')
    sar_path = ('/logs/fu/var/log/sa/', '/logs/sc/sar/')

    for path in sar_path:
        try:
            sar_files = glob.glob(path + "sa????????")
            for file in sar_files:
                logging.debug(f'load_data() - Found file: {file}')
                create_db(file)
                create_tables(file,OPTIONS)
        except:
            logging.warn(f'load_data() - Warn: An error occured collecting sar file {file}')

    logging.info('load_data() - Waiting for new events ...')


def main():
    """ Triggers the function load_data() if there are any changes in logs/ folder"""
    logging.info('main() - Starting main()')
    load_data()
    i = inotify.adapters.InotifyTree('/logs')

    for event in i.event_gen(yield_nones=False):
        (_, type_names, _, _) = event

        if 'IN_CREATE' in type_names or 'IN_DELETE' in type_names:
            logging.info('main() - Event action: sar content has been changed. Reload data...')
            load_data()


if __name__ == "__main__":
    main()
