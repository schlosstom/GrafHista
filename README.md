# GrafHista

Especially for support it is often usefull to have an overview about different logs in a special timeframe. 

SAP is using a so called "HANA Full System Info Dump" (see SAP Note 2573880 - FAQ: SAP HANA Full System Info Dump) for collecting data when something goes wrong and they need to analyse customer systems. Such a dump provides also all the trace file from a special timeframe. The idea is to use **GrafHista** for analysing these traces as well. 

To gain first experiences in capturing offline traces and logs I've created three  Docker container. One is a normal Grafana container, one is a mysql container and the last one contains promtail, loki and logcli.

### How to use:

All logs should be placed in a subfolder under logs/ (for example: logs/**my-trace/**). 

The following command will create and start **GrafHista**:

**docker-compose up -d**

**Important:** At the moment **GrafHista** is a **Beta** version and only a few files can be used for analyzing. 


#### Why is this project named GrafHista:
In the very beginning of the idea to collect offline data, I've put all the code into the [GrafHana](https://gitlab.suse.de/tschloss/grafhana/) project as additional feature. Using additional different container and the fact that it can 
not only capturing HANA specific data I deside to move it to a separate project.

Therefore a new namen was needed. The name contains the words **Grafana**, **History** and **analyze** in it. In other words:

**Analyzing historical data with Grafana.**



## Examples:
There are are ready some example logs under **logs/examples** for plaing around,


#### OS logfile 

external path: logs/examples/messages.txt    

Labels: 
- **job:** messages
- **host:** ext
- **filename:** /var/log/examples/messages.txt

Please adjust the date around **2022-12-12** in Grafana Dashboard

#### Nameserver trace file 

external path: logs/examples/nameserver_hana01.00000.000.trc

- **job:** nameserver
- **host:** ext
- **filename:** /var/log/mytest/nameserver_hana01.00000.000.trc

Please adjust the date around **2022-12-07** in Grafana Dashboard


#### System availability trace file

external path: logs/examples/system_availability_hana01.trc

Labels: 
- **job:** service-available
- **host:** ext
- **filename:** /var/log/examples/system_availability_hana01.trc

Please adjust the date around **2022-12-11 - 2022-12-13** in Grafana Dashboard

#### SAR files

external path:  logs/examples/sa20220317

The script **create_sar_db.py** can be used to create a mysql database for each 
sar binary file. The database will then include the content of the sar data in form of different tables. 

The script needs the mysql module:

    zypper in python3-mysql-connector-python


**Important:** The script is currently in a very **early alpha phase** and needs to inproved.

The script has to be run localy outside of the container. 

Example:

```bash
/usr/bin/python3 create_sar_db.py -f logs/examples/sa20220317
Database: sa20220317 created
    Table: kernel created
    Table: cpu_load created
    Table: paging created
    Table: memory created
    Table: swap_pages created
    Table: queue created
```


On the Grafana dashboard mysql has to add as an additional source with following settings:

**Host:** mysql  
**User:** root  
**Password:** Suse1234  

There is already a minimalistic Grafana Dashboard named **Sar** where each of 
the created databases (sar files)  can be selected.