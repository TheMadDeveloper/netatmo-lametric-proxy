#!/usr/bin/python
# encoding=utf-8

from library import lnetatmo
from library import lametric
from library import SunriseSunset
from library.tzlocal import get_localzone
import datetime
import time
import pytz
import json
import os.path
import ConfigParser

# Netatmo / LaMetric Proxy
# Author : Stanislav Likavcan, likavcan@gmail.com

# A simple client which turns LaMetric into Netamo display. This client calls Netatmo API and updates LaMetric display 
# Easiest way to keep the LaMetric display updated is via cron task:
# */10 * * * * /home/lametric/updateLaMetric.py
# Don't forget to create an app within both Netatmo and LaMetric and provide your credentials here:

scriptDir = os.path.dirname(os.path.abspath(__file__))

config = ConfigParser.ConfigParser()
config.read("%s/config-tinversion.ini"%(scriptDir))

# Netatmo authentication
client_id     = config.get('netatmo','client_id')
client_secret = config.get('netatmo','client_secret')
username      = config.get('netatmo','username')
password      = config.get('netatmo','password')

# LaMetric authentication
access_token  = config.get('lametric','access_token')
app_id        = config.get('lametric','app_id')

# Display preferences
temp_units    = config.get('display','temperature_units')

# Use Celsius unless the config file is attempting to set things to Farenheit
temp_units = 'C' if temp_units[0].upper() != 'F' else 'F'

# Initiate Netatmo client
authorization = lnetatmo.ClientAuth(client_id, client_secret, username, password)
devList = lnetatmo.DeviceList(authorization)
theData = devList.lastData()

# Location GPS coordinates from Netatmo
lng, lat = devList.locationData()['location']

# Calculate the local timezone offset
now = datetime.datetime.now()
utc = get_localzone().localize(now).astimezone(pytz.utc).replace(tzinfo=None)
localOffset =  (utc - now).seconds / -3600

ro = SunriseSunset.Setup(datetime.datetime.now(), latitude=lat, longitude=lng, localOffset = localOffset)
rise_time, set_time = ro.calculate()

for module in theData.keys():
    print module
    m_id = theData[module]['id']
    m_type = theData[module]['type']
    m_data_type = theData[module]['data_type']
    m_data = ', '.join(m_data_type)
    if (m_type == 'NAMain'):
        station_name = module
        station_id   = m_id
        print "Detected station: %s '%s' - %s, %s" % (m_id, module, m_type, m_data)
    elif (m_type == 'NAModule1' and 'CO2' not in m_data_type):
        module_name = module
        module_id   = m_id
        print "Detected module : %s '%s' - %s, %s" % (m_id, module, m_type, m_data)
    else:
        print "Detected other  : %s '%s' - %s, %s" % (m_id, module, m_type, m_data)

now   = time.time();
# Retrieve data from midnight until now
#today = time.strftime("%Y-%m-%d")
#today = int(time.mktime(time.strptime(today,"%Y-%m-%d")))
# Retrieve data for last 24hours
last_day  = now - 36 * 3600;

print "Temps from %s to %s" % (last_day, now)

measure = devList.getMeasure(station_id, '1hour', 'Temperature', module_id, date_begin = last_day, date_end = now, optimize = True)

# Convert temperature values returned by Netatmo to simple field
hist_temp = [int(round(v[0],0)) for v in measure['body'][0]['value']]

print theData

# Retrieve current sensor data
outdoor = {}

indoorTemp = theData[station_name]['Temperature']
outdoorTemp = theData[module_name]['Temperature']

# Convert to Farenheit as needed
if temp_units == 'F' :
    indoorTemp = indoorTemp * 1.8 + 32
    outdoorTemp = outdoorTemp * 1.8 + 32

dt =  outdoorTemp - indoorTemp

outdoor['temperature'] = str(outdoorTemp) + "°" + temp_units
outdoor['humidity']    = str(theData[module_name]['Humidity'])+'%'
outdoor['pressure']    = str(theData[station_name]['Pressure'])+'mb'
outdoor['trend']       = str(theData[station_name]['pressure_trend'])

print "Temperature Difference %s°%s" % (indoorTemp - outdoorTemp, temp_units)

dataFile = "%s/data.json" % (scriptDir)

with open(dataFile,'r') as f:
    prev = json.load(f)
    print "Last reading %s %s @ %s seconds ago" % (prev[u'dt'], prev[u'unit'], now - prev[u'time'])

with open(dataFile,'w') as f:
    json.dump({'dt': dt, "unit": temp_units, "time": now}, f)

sign = '+' if dt > 0 else ''
dtDisplay = "%s%.1f%s" % (sign,dt, "°"+temp_units)
msg = "Warmer Outside" if sign == '+' else "Cooler Outside"

if prev[u'dt'] * dt < 0 or True :
    # Post data to LaMetric
    lametric = lametric.Setup()
    lametric.addTextFrame('i2870',msg)
    lametric.addTextFrame('i2870',dtDisplay)
    lametric.addSparklineFrame(hist_temp)
    lametric.push(app_id, access_token)
