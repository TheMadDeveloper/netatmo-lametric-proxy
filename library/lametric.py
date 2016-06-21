# PythonAPI LaMetric REST data access
# coding=utf-8

from sys import version_info
import json
import urllib2
import ssl

# Common definitions

_HOST       = "https://developer.lametric.com"
_PUSH_PATH   = "/api/v1/dev/widget/update/com.lametric."

class Setup(object):

    def __init__(self, local_address=False):
        self.data = {}
        self.data['frames'] = []
        self.index = 0
        host = local_address if local_address else _HOST
        self.push_url = host + _PUSH_PATH

    def addTextFrame(self, icon, text):
        frame = {}
        frame['index'] = self.index
        frame['icon']  = icon
        frame['text']  = text
        self.data['frames'].append(frame)
        self.index += 1

    def addGoalFrame(self, icon, start, current, end, unit):
        frame = {}
        frame['index'] = self.index
        frame['icon']  = icon
        frame['goalData'] = {}
        frame['goalData']['start'] = start
        frame['goalData']['current'] = current 
        frame['goalData']['end'] = end
        frame['goalData']['unit'] = unit
        self.data['frames'].append(frame)
        self.index += 1

    def addSparklineFrame(self, data):
        frame = {}
        frame['index'] = self.index
        frame['chartData'] = data
        self.data['frames'].append(frame)
        self.index += 1
    
    def push(self, app_id, access_token, local_address=False):
        if version_info.micro > 9:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            opener = urllib2.build_opener(urllib2.HTTPSHandler(context=ctx));
        else:
            opener = urllib2.build_opener();
        
        headers = { 'Accept': 'application/json', 'Cache-Control': 'no-cache', 'X-Access-Token': access_token };
        
        request = urllib2.Request(self.push_url+app_id, json.dumps(self.data,ensure_ascii=False), headers);

        print json.dumps(self.data,ensure_ascii=False)

        try:
            response = opener.open(request);
        except urllib2.HTTPError as e:
            print('The server couldn\'t fulfill the request.')
            print('Error code: ', e.code)
            print e.read()
        except urllib2.URLError as e:
            print('Failed to reach a server.')
            print('Reason: ', e.reason)
            print e.read()
        #else:
            # everything is fine

