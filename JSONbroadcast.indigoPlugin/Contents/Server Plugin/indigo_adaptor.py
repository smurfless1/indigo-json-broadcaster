from datetime import date, datetime
import time as time_
import json
from typing import Optional, Union

import indigo


def indigo_json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    # indigo.server.log(str(obj))
    if isinstance(obj, (datetime, date)):
        ut = time_.mktime(obj.timetuple())
        return int(ut)
    if isinstance(obj, indigo.Dict):
        dd = {}
        for key, value in obj.iteritems():
            dd[key] = value
        return dd
    raise TypeError("Type %s not serializable" % type(obj))


class IndigoAdaptor:
    """
    Change indigo objects to flat dicts for simpler databases
    """

    def __init__(self):
        self.debug = False
        # Class Properties on http://wiki.indigodomo.com/doku.php?id=indigo_7_documentation:device_class
        self.string_only_keys = (
            "displayStateValRaw displayStateValUi displayStateImageSel protocol".split()
        )

        # have the json serializer always use this
        json.JSONEncoder.default = indigo_json_serial

        # remember previous states for diffing, smaller databases
        self.cache = {}
        # remember column name/type mappings to reduce exceptions
        self.type_mapping_cache = {}

    @staticmethod
    def smart_value(in_value, make_numbers=False) -> Optional[Union[int, float, str, bool]]:
        """
        Try to be smarter about what the value is

        As in remembering type across updates, which is a problem sometimes.

        @return: None or a value, trying to convert strings to floats where possible
        """
        value = None
        if (
                in_value != "null"
                and in_value != "None"
                and not isinstance(in_value, indigo.List)
                and not isinstance(in_value, list)
                and not isinstance(in_value, indigo.Dict)
                and not isinstance(in_value, dict)
        ):
            value = in_value
            try:
                if make_numbers:
                    # early exit if we want a number but already have one
                    if isinstance(in_value, float):
                        value = None
                    elif isinstance(in_value, (datetime, date)):
                        value = None
                    # if we have a string, but it really is a number,
                    # MAKE IT A NUMBER IDIOTS
                    elif isinstance(in_value, str):
                        value = float(in_value)
                    elif isinstance(in_value, int):
                        value = float(in_value)
                elif isinstance(in_value, bool):
                    # bypass for bools - getting cast as ints
                    value = bool(in_value)
                elif isinstance(in_value, int):
                    # convert ALL numbers to floats for influx
                    value = float(in_value)
                # convert datetime to timestamps of another flavor
                elif isinstance(in_value, (datetime, date)):
                    value = time_.mktime(in_value.timetuple())
                    # value = int(ut)
                # explicitly change enum values to strings
                # TODO find a more reliable way to change enums to strings
                elif in_value.__class__.__bases__[0].__name__ == "enum":
                    value = str(in_value)
            except ValueError:
                if make_numbers:
                    # if we were trying to force numbers but couldn't
                    value = None
                pass
        return value

    def to_json(self, device):
        """
        Reformat the whole device update to suitable JSON
        """
        attribute_list = [
            attr
            for attr in dir(device)
            if attr[:2] + attr[-2:] != "____" and not callable(getattr(device, attr))
        ]
        # indigo.server.log(device.name + ' ' + ' '.join(attribute_list))
        new_json = {"name": str(device.name)}
        for key in attribute_list:
            # import pdb; pdb.set_trace()
            if hasattr(device, key) and key not in new_json.keys():
                val = self.smart_value(getattr(device, key), False)
                # some things change types - define the original name as original type, key.num as numeric
                if val is not None:
                    new_json[key] = val
                if key in self.string_only_keys:
                    continue
                val = self.smart_value(getattr(device, key), True)
                if val is not None:
                    new_json[key + ".num"] = val

        # trouble areas
        # dicts end enums will not upload without a little abuse
        for key in "states globalProps pluginProps ownerProps".split():
            if key in new_json.keys():
                del new_json[key]

        for key in new_json.keys():
            if new_json[key].__class__.__name__.startswith("k"):
                new_json[key] = str(new_json[key])

        for key in self.string_only_keys:
            if key in new_json.keys():
                new_json[key] = str(new_json[key])

        for state in device.states:
            val = self.smart_value(device.states[state], False)
            if val is not None:
                new_json[str("state." + state)] = val
            if state in self.string_only_keys:
                continue
            val = self.smart_value(device.states[state], True)
            if val is not None:
                new_json[str("state." + state + ".num")] = val

        # Try to tell the caller what kind of measurement this is
        if "setpointHeat" in device.states.keys():
            new_json["measurement"] = "thermostat_changes"
        elif device.model == "Weather Station":
            new_json["measurement"] = "weather_changes"
        else:
            new_json["measurement"] = "device_changes"

        # try to honor previous complaints about column types
        for key in self.type_mapping_cache.keys():
            if key in new_json.keys():
                try:
                    new_json[key] = eval(
                        '%s("%s")' % (self.type_mapping_cache[key], str(new_json[key]))
                    )
                except ValueError:
                    if self.debug:
                        indigo.server.log(
                            "One of the columns just will not convert to the requested type. Partial record written."
                        )
                    pass

        return new_json

    def diff_to_json(self, device):
        # strip out matching values?
        # find or create our cache dict
        new_json = self.to_json(device)

        localcache = {}
        if device.name in self.cache.keys():
            localcache = self.cache[device.name]

        diffjson = {}
        for kk, vv in new_json.items():
            if kk not in localcache or localcache[kk] != vv:
                if not isinstance(vv, indigo.Dict) and not isinstance(vv, dict):
                    diffjson[kk] = vv

        if device.name not in self.cache.keys():
            self.cache[device.name] = {}
        self.cache[device.name].update(new_json)

        # always make sure these survive
        diffjson["name"] = device.name
        diffjson["id"] = float(device.id)
        diffjson["measurement"] = new_json["measurement"]

        if self.debug:
            indigo.server.log(
                json.dumps(new_json, default=indigo_json_serial).encode("utf-8")
            )
            indigo.server.log("diff:")
            indigo.server.log(
                json.dumps(diffjson, default=indigo_json_serial).encode("utf-8")
            )

        return diffjson
