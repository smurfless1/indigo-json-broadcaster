#! /usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2017-22, Dave Brown
#
import socket
import indigo
import json
from indigo_adaptor import IndigoAdaptor, smart_value

MCAST_GRP = "224.1.1.1"
MCAST_PORT = 8087


class Plugin(indigo.PluginBase):
    """A plugin to broadcast device and variable changes over multicast."""
    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        super(Plugin, self).__init__(
            pluginId, pluginDisplayName, pluginVersion, pluginPrefs
        )
        indigo.devices.subscribeToChanges()
        indigo.variables.subscribeToChanges()
        self.connection = None
        self.adaptor = IndigoAdaptor()
        self.folders = {}

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        self.sock.bind("0.0.0.0")  # send over all the v4 addresses anyway
        self.port = None

    def send(self, tags, what, measurement="device_changes"):
        """Send this a dict of what to write."""
        json_body = [{"measurement": measurement, "tags": tags, "fields": what}]

        output = json.dumps(json_body).encode("utf-8")
        if self.pluginPrefs.get("debug", False):
            indigo.server.log(output)

        self.sock.sendto(output, (MCAST_GRP, self.port))  # returns bool if needed

    def startup(self):
        """Start up the server."""
        self.port = int(self.pluginPrefs.get("port", "8086"))

    def shutdown(self):
        """Called after runConcurrentThread exits"""
        pass

    def deviceUpdated(self, origDev, newDev):
        """Called when a device is updated."""
        # call base implementation
        indigo.PluginBase.deviceUpdated(self, origDev, newDev)

        # custom add to influx work
        # tag by folder if present
        tag_names = "name folderId".split()
        new_json = self.adaptor.diff_to_json(newDev)

        new_tags = {}
        for tag in tag_names:
            new_tags[tag] = str(getattr(newDev, tag))

        # add a folder name tag
        if hasattr(newDev, "folderId") and newDev.folderId != 0:
            new_tags["folder"] = indigo.devices.folders[newDev.folderId].name

        measurement = new_json["measurement"]
        del new_json["measurement"]
        self.send(tags=new_tags, what=new_json, measurement=measurement)

    def variableUpdated(self, origVar, newVar):
        """Called when a variable is updated."""
        indigo.PluginBase.variableUpdated(self, origVar, newVar)

        new_tags = {"varname": newVar.name}
        new_json = {"name": newVar.name, "value": newVar.value}
        numeric = smart_value(newVar.value, True)
        if numeric is not None:
            new_json["value.num"] = numeric

        self.send(tags=new_tags, what=new_json, measurement="variable_changes")
