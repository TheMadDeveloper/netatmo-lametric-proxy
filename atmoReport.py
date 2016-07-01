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

# Globals
scriptDir = os.path.dirname(os.path.abspath(__file__))
localtime = time.time()

def main():

    config = ConfigParser.ConfigParser()
    config.read("%s/config.ini"%(scriptDir))

    # Netatmo authentication
    client_id     = config.get('netatmo','client_id')
    client_secret = config.get('netatmo','client_secret')
    username      = config.get('netatmo','username')
    password      = config.get('netatmo','password')

    # Display preferences
    temp_units    = config.get('display','temperature_units')

    # Use Celsius unless the config file is attempting to set things to Farenheit
    temp_units = 'C' if temp_units[0].upper() != 'F' else 'F'

    # Initiate Netatmo client
    authorization = lnetatmo.ClientAuth(client_id, client_secret, username, password)
    devList = lnetatmo.DeviceList(authorization)
    theData = devList.lastData()

    now = datetime.datetime.now()
    rise_time, set_time = getSunEvents(devList, now)

    show_sunrise = now > set_time or now < rise_time

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

    #now   = time.time();
    # Retrieve data from midnight until now
    #today = time.strftime("%Y-%m-%d")
    #today = int(time.mktime(time.strptime(today,"%Y-%m-%d")))
    # Retrieve data for last 24hours
    # last_day  = now - 36 * 3600;

    # measure = devList.getMeasure(station_id, '1hour', 'Temperature', module_id, date_begin = now-19*3600, date_end = now, optimize = True)

    # # Get a combined indoor and outdoor sparkline
    # outdoor_hist_temp = [int(round(v[0],0)) for v in measure['body'][0]['value']]

    # measure = devList.getMeasure(station_id, '1hour', 'Temperature', date_begin = now-19*3600, date_end = now, optimize = True)

    # # Convert temperature values returned by Netatmo to simple field
    # indoor_hist_temp = [int(round(v[0],0)) for v in measure['body'][0]['value']]

    # hist_temp = range(0,37)

    # for i in range(0,18) :
    #     hist_temp[i*2] = outdoor_hist_temp[i]
    #     hist_temp[i*2+1] = indoor_hist_temp[i]

    # hist_temp[36] = outdoor_hist_temp[18]
    measure = devList.getMeasure(station_id, '1hour', 'Temperature', date_begin = localtime-18*3600, date_end = localtime, optimize = True)
    hist_temp = amplifyTemps([int(round(v[0],0)) for v in measure['body'][0]['value']])

    measure = devList.getMeasure(station_id, '30min', 'CO2', date_begin = localtime-18*3600, date_end = localtime, optimize = True)
    hist_co2 = [int(round(v[0],0)) for v in measure['body'][0]['value']]

    # up down or stable
    tempTrend = theData[module_name]['temp_trend']

    # Retrieve current sensor data
    outdoor = {}

    indoorTemp = theData[station_name]['Temperature']
    outdoorTemp = theData[module_name]['Temperature']

    # Convert to Farenheit as needed
    if temp_units == 'F' :
        indoorTemp = indoorTemp * 1.8 + 32
        outdoorTemp = outdoorTemp * 1.8 + 32

    dt = outdoorTemp - indoorTemp
    sign = '+' if dt > 0 else ''

    combinedTemp = "%.0f%s%.0f°" % (indoorTemp,sign,dt)

    outdoor['temperature'] = combinedTemp

    print outdoor

    # Icons definition
    icon = {
        'tempStable': 'i2925',
        'tempUp': 'a2928',
        'tempDown': 'a2924',
        'co2': 'i2033',
        'tempC': 'i2056',
        'humi': 'i863',
        'stable': 'i401',
        'up': 'i120',
        'down': 'i124',
        #pretty sun 'sunrise': 'i2282',
        #josemarq 'sunset': 'a2871',
        'sunset': 'a2871',
        'sunrise': 'a2282'
    }

    time_format = config.get('display','time_format')

    # Post data to LaMetric
    localhost = config.get('lametric','local_ip')
    lm = lametric.Setup(localhost)

    lm.addTextFrame(icon['tempStable'],outdoor['temperature'])
    lm.addSparklineFrame(hist_temp)
    lm.addTextFrame(icon['co2'],"%i%s" % (theData[station_name]['CO2'],""))
    lm.addSparklineFrame(hist_co2)
    if show_sunrise :
        lm.addTextFrame(icon['sunrise'],rise_time.strftime(time_format))
    else :
        lm.addTextFrame(icon['sunset'],set_time.strftime(time_format))

    # lametric.addTextFrame(icon['sunset'],set_time.strftime(time_format))
    lm.push(config.get("lametric","atmo_app_id"), config.get("lametric","access_token"))

    inversionEvent, msg, dtDisplay = checkTempInversion(dt, temp_units)
    if inversionEvent :
        # Post data to LaMetric
        lm = lametric.Setup(localhost)
        lm.addTextFrame('i2870',msg)
        lm.addTextFrame('i2870',dtDisplay)
        lm.addSparklineFrame(hist_temp)
        lm.push(config.get("lametric","tinv_app_id"), config.get("lametric","access_token"))

def getSunEvents(devList, now):
    # Location GPS coordinates from Netatmo
    lng, lat = devList.locationData()['location']

    # Calculate the local timezone offset
    utc = get_localzone().localize(now).astimezone(pytz.utc).replace(tzinfo=None)
    localOffset =  (utc - now).seconds / -3600

    ro = SunriseSunset.Setup(datetime.datetime.now(), latitude=lat, longitude=lng, localOffset = localOffset)
    return ro.calculate()

def amplifyTemps(data):
    maxVal = max(data)
    minVal = min(data)
    return [v-minVal for v in data]

def checkTempInversion(dt, temp_units):
    print "Temperature Difference %s°%s" % (dt, temp_units)

    dataFile = "%s/data.json" % (scriptDir)
    inversionEvent = False

    try:
        with open(dataFile,'r') as f:
            prev = json.load(f)
            print "Last reading %s %s @ %s seconds ago" % (prev[u'dt'], prev[u'unit'], localtime - prev[u'time'])
            inversionEvent = (prev[u'dt'] * dt < 0)
    except ValueError:
        print "No previous reading"

    with open(dataFile,'w') as f:
       json.dump({'dt': dt, "unit": temp_units, "time": localtime}, f)


    sign = '+' if dt > 0 else ''
    dtDisplay = "%s%.1f%s" % (sign,dt, "°"+temp_units)
    msg = "Warmer Outside" if sign == '+' else "Cooler Outside"

    return inversionEvent, msg, dtDisplay

if __name__ == "__main__": main()

