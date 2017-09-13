#! /usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2017, Dave Brown
#
import socket
import indigo
import time as time_
from datetime import datetime, date
import json
from indigo_adaptor import IndigoAdaptor

MCAST_GRP = '224.1.1.1'
MCAST_PORT = 8086

class Plugin(indigo.PluginBase):
    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        super(Plugin, self).__init__(pluginId, pluginDisplayName, pluginVersion, pluginPrefs)
        indigo.devices.subscribeToChanges()
        indigo.variables.subscribeToChanges()
        self.connection = None
        self.adaptor = IndigoAdaptor()
        self.folders = {}

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)


    # send this a dict of what to write
    def send(self, tags, what, measurement='device_changes'):
        json_body=[
            {
                'measurement': measurement,
                'tags' : tags,
                'fields':  what
            }
        ]

        if self.pluginPrefs.get(u'debug', False):
            indigo.server.log(json.dumps(json_body).encode('utf-8'))

        self.sock.sendto(json.dumps(json_body).encode('utf-8'), (MCAST_GRP, self.port))  # returns bool if needed

    def startup(self):
        self.port = int(self.pluginPrefs.get('port', '8086'))

# called after runConcurrentThread() exits
    def shutdown(self):
        pass

    def deviceUpdated(self, origDev, newDev):
        # call base implementation
        indigo.PluginBase.deviceUpdated(self, origDev, newDev)

        # custom add to influx work
        # tag by folder if present
        tagnames = u'name folderId'.split()
        newjson = self.adaptor.diff_to_json(newDev)

        newtags = {}
        for tag in tagnames:
            newtags[tag] = unicode(getattr(newDev, tag))

        # add a folder name tag
        if hasattr(newDev, u'folderId') and newDev.folderId != 0:
            newtags[u'folder'] = indigo.devices.folders[newDev.folderId].name

        measurement = newjson[u'measurement']
        del newjson[u'measurement']
        self.send(tags=newtags, what=newjson, measurement=measurement)

    def variableUpdated(self, origVar, newVar):
        indigo.PluginBase.variableUpdated(self, origVar, newVar)

        newtags = {u'varname': newVar.name}
        newjson = {u'name': newVar.name, u'value': newVar.value }
        numval = self.adaptor.smart_value(newVar.value, True)
        if numval != None:
            newjson[u'value.num'] = numval

        self.send(tags=newtags, what=newjson, measurement=u'variable_changes')

