import socket
from typing import Any

import indigo
import json
from indigo_adaptor import IndigoAdaptor

MCAST_GRP = "224.1.1.1"
MCAST_PORT = 8087
MCAST_TTL = 2


class Plugin(indigo.PluginBase):
    def __init__(self, pluginId, pluginDisplayName, pluginVersion, pluginPrefs):
        super(Plugin, self).__init__(
            pluginId, pluginDisplayName, pluginVersion, pluginPrefs
        )
        self.port = MCAST_PORT
        indigo.devices.subscribeToChanges()
        indigo.variables.subscribeToChanges()
        self.connection = None
        self.adaptor = IndigoAdaptor()
        self.folders = {}

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, MCAST_TTL)

    def send(
        self,
        tags: dict[str, str],
        what: dict[str, Any],
        measurement: str = "device_changes",
    ):
        """This sends a dict over multicast."""
        json_body = [{"measurement": measurement, "tags": tags, "fields": what}]

        if self.pluginPrefs.get("debug", False):
            indigo.server.log(json.dumps(json_body).encode("utf-8"))

        self.sock.sendto(
            json.dumps(json_body).encode("utf-8"), (MCAST_GRP, self.port)
        )  # returns bool if needed

    def startup(self):
        self.port = int(self.pluginPrefs.get("port", MCAST_PORT))

    def shutdown(self):
        """Called after runConcurrentThread() exits"""
        pass

    def deviceUpdated(self, origDev, newDev):
        """
        Update from origDev to newDev
        """
        # call base implementation
        indigo.PluginBase.deviceUpdated(self, origDev, newDev)

        # custom add to influx work
        # tag by folder if present
        tag_names = "name folderId".split()
        new_json = self.adaptor.diff_to_json(newDev)

        new_tags: dict[str, str] = {}
        for tag in tag_names:
            new_tags[tag] = str(getattr(newDev, tag))

        # add a folder name tag
        if hasattr(newDev, "folderId") and newDev.folderId != 0:
            new_tags["folder"] = indigo.devices.folders[newDev.folderId].name

        measurement = new_json["measurement"]
        del new_json["measurement"]
        self.send(tags=new_tags, what=new_json, measurement=measurement)

    def variableUpdated(self, origVar, newVar):
        indigo.PluginBase.variableUpdated(self, origVar, newVar)

        new_tags: dict[str, str] = {"varname": newVar.name}
        new_json: dict[str, Any] = {"name": newVar.name, "value": newVar.value}
        numeric_value = self.adaptor.smart_value(newVar.value, True)
        if numeric_value is not None:
            new_json["value.num"] = numeric_value

        self.send(tags=new_tags, what=new_json, measurement="variable_changes")
