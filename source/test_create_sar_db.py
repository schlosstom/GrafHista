#! /usr/bin/python3


import pprint
import subprocess
import json
import sys 
from pathlib import Path

from datetime import datetime


file = "/logs/sc/sar/sa20230417"
#option = "-r"        # mem
#option = "-P ALL"    # cpus
#option = "-n DEV"    # network
 

def test_run(option): 
    commands = "sadf -j " + file + " -- " + option
    command = commands.split()
    dict = json.loads(subprocess.check_output( command,  encoding='UTF-8'))
    return dict


key_name01 = " "
key_name02 = " "

# Mem
dict = test_run("-r")
path = dict['sysstat']['hosts'][0]['statistics'][0]

key_name01 = (set(path.keys()) - {'timestamp'}).pop()
item = path[key_name01]

print(key_name01)
print("-------------")
print(item)

print(" ")
print(" ")





# cpus (-P ALL)
dict = test_run("-P ALL")
path = dict['sysstat']['hosts'][0]['statistics'][0]

key_name01 = (set(path.keys()) - {'timestamp'}).pop()
item = path[key_name01][0] 

print(key_name01)
print("-------------")
print(item)

print(" ")
print(" ")


# Network (-n DEV)
dict = test_run("-n DEV")
path = dict['sysstat']['hosts'][0]['statistics'][0]

key_name01= (set(path.keys()) - {'timestamp'}).pop()
key_name02 = (set(path[key_name01].keys()) - {'network'}).pop()

item = path[key_name01][key_name02][0]

print(key_name01)
print(key_name02)
print("-------------")
print(item)

# pprint.pprint(path)
