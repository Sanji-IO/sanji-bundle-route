#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import os
import netifaces
import logging
from time import sleep
from sanji.core import Sanji
from sanji.core import Route
from sanji.connection.mqtt import Mqtt
from sanji.model_initiator import ModelInitiator
from voluptuous import Schema
from voluptuous import Any, Extra, Optional

import ip


_logger = logging.getLogger("sanji.route")


class IPRoute(Sanji):
    """
    A model to handle IP Route configuration.

    Attributes:
        model: database with json format.
    """

    update_interval = 60

    def init(self, *args, **kwargs):
        try:  # pragma: no cover
            self.bundle_env = kwargs["bundle_env"]
        except KeyError:
            self.bundle_env = os.getenv("BUNDLE_ENV", "debug")

        path_root = os.path.abspath(os.path.dirname(__file__))
        if self.bundle_env == "debug":  # pragma: no cover
            path_root = "%s/tests" % path_root

        self.interfaces = []
        try:
            self.load(path_root)
        except:
            self.stop()
            raise IOError("Cannot load any configuration.")

    def run(self):
        while True:
            try:
                self.try_update_default(self.model.db)
            except:
                pass
            sleep(self.update_interval)

    def load(self, path):
        """
        Load the configuration. If configuration is not installed yet,
        initialise them with default value.

        Args:
            path: Path for the bundle, the configuration should be located
                under "data" directory.
        """
        self.model = ModelInitiator("route", path, backup_interval=-1)
        if self.model.db is None:
            raise IOError("Cannot load any configuration.")
        self.save()

    def save(self):
        """
        Save and backup the configuration.
        """
        self.model.save_db()
        self.model.backup_db()

    def list_interfaces(self):
        """
        List available interfaces.
        """
        # retrieve all interfaces
        try:
            ifaces = ip.addr.interfaces()
        except:
            return {}

        # list connected interfaces
        data = []
        for iface in ifaces:
            try:
                iface_info = ip.addr.ifaddresses(iface)
            except:
                continue
            if 1 == iface_info["link"]:
                data.append(iface)
        return data

    def get_default(self):
        """
        Retrieve the default gateway

        Return:
            default: dict format with "interface" and/or "gateway"
        """
        gws = netifaces.gateways()
        default = {}
        if gws['default'] != {}:
            gw = gws['default'][netifaces.AF_INET]
        else:
            return default

        default["gateway"] = gw[0]
        default["interface"] = gw[1]
        return default

    def update_dns(self, interface):
        """
        Update DNS according to default gateway's interface.

        Args:
            default: interface name
        """
        res = self.publish.put("/network/dns", data={"interface": interface})
        if res.code != 200:
            raise RuntimeWarning(res.data["message"])

    def update_default(self, default):
        """
        Update default gateway. If updated failed, should recover to previous
        one.

        Args:
            default: dict format with "interface" required and "gateway"
                     optional.
        """
        # delete the default gateway
        if not default or ("interface" not in default and
                           "gateway" not in default):
            try:
                ip.route.delete("default")
            except Exception as e:
                raise e

        # change the default gateway
        # FIXME: only "gateway" without interface is also available
        # FIXME: add "secondary" default route rule
        else:
            try:
                ip.route.delete("default")
                if "gateway" in default and "interface" in default:
                    ip.route.add("default", default["interface"],
                                 default["gateway"])
                elif "interface" in default:
                    ip.route.add("default", default["interface"])
                elif "gateway" in default:
                    ip.route.add("default", "", default["gateway"])
                else:
                    raise ValueError("Invalid default route.")

                # update DNS
                if "interface" in default:
                    self.update_dns(default["interface"])
            except Exception as e:
                raise e

    def try_update_default(self, routes):
        """
        Try to update the default gateway.

        Args:
            routes: dict format including default gateway interface and
                    secondary default gateway interface.
                    For example:
                    {
                        "default": "wwan0",
                        "secondary": "eth0"
                    }
        """
        ifaces = self.list_interfaces()
        if not ifaces:
            raise ValueError("Interfaces should be UP.")

        default = {}
        if routes["default"] in ifaces:
            default["interface"] = routes["default"]
        elif routes["secondary"] in ifaces:
            default["interface"] = routes["secondary"]
        else:
            return self.update_default({})

        # find gateway by interface
        for iface in self.interfaces:
            if iface["interface"] == default["interface"]:
                default = iface
                break

        current = self.get_default()
        try:
            if current["interface"] != default["interface"] or \
                    current["gateway"] != default["gateway"]:
                self.update_default(default)
        except:
            self.update_default(default)

    def update_router(self, interface):
        """
        Save the interface name with its gateway and update the default
        gateway if needed.

        If gateway is not specified, use the previous value. Only delete the
        gateway when gateway attribute is empty.

        Args:
            interface: dict format with interface "name" and/or "gateway".
        """
        # update the router information
        for iface in self.interfaces:
            if iface["interface"] == interface["name"]:
                if "gateway" in interface:
                    iface["gateway"] = interface["gateway"]
                break
        else:
            iface = {}
            iface["interface"] = interface["name"]
            if "gateway" in interface:
                iface["gateway"] = interface["gateway"]
            self.interfaces.append(iface)

        # check if the default gateway need to be modified
        if iface["interface"] == self.model.db["default"]:
            try:
                self.try_update_default(self.model.db)
            except:
                pass

    def set_default(self, default, is_default=True):
        """
        Update default / secondary gateway.
        """
        if is_default:
            def_type = "default"
        else:
            def_type = "secondary"

        # save the setting
        # if no interface but has gateway, do not update anything
        if "interface" in default:
            self.model.db[def_type] = default["interface"]
        elif "gateway" not in default:
            self.model.db[def_type] = ""
        self.save()

        try:
            if is_default:
                self.update_default(default)
        except Exception as e:
            # try database if failed
            try:
                self.try_update_default(self.model.db)
            except:
                _logger.info("Failed to recover the default gateway.")
            error = "Update default gateway failed: %s" % e
            _logger.error(error)
            raise IOError(error)

    @Route(methods="get", resource="/network/routes/interfaces")
    def _get_interfaces(self, message, response):
        """
        Get available interfaces.
        """
        return response(data=self.list_interfaces())

    @Route(methods="get", resource="/network/routes/default")
    def _get_default(self, message, response):
        """
        Get default gateway.
        """
        return response(data=self.get_default())

    put_default_schema = Schema({
        Optional("interface"): Any(str, unicode),
        Extra: object})

    @Route(methods="put", resource="/network/routes/default")
    def _put_default(self, message, response, schema=put_default_schema):
        """
        Update the default gateway, delete default gateway if data is None or
        empty.
        """
        try:
            self.set_default(message.data)
        except Exception as e:
            return response(code=404,
                            data={"message": e})
        return response(data=self.get_default())

    @Route(methods="put", resource="/network/routes/secondary")
    def _put_secondary(self, message, response, schema=put_default_schema):
        """
        Update the secondary default gateway, delete default gateway if data
        is None or empty.
        """
        try:
            self.set_default(message.data, False)
        except Exception as e:
            return response(code=404,
                            data={"message": e})
        return response(data=message.data)

    def set_router_db(self, message, response):
        """
        Update router database batch or by interface.
        """
        if type(message.data) is list:
            for iface in message.data:
                self.update_router(iface)
            return response(data=self.interfaces)
        elif type(message.data) is dict:
            self.update_router(message.data)
            return response(data=message.data)
        return response(code=400,
                        data={"message": "Wrong type of router database."})

    @Route(methods="put", resource="/network/routes/db")
    def _set_router_db(self, message, response):
        return self.set_router_db(message, response)

    @Route(methods="get", resource="/network/routes/db")
    def _get_router_db(self, message, response):
        return response(data=self.interfaces)

    @Route(methods="put", resource="/network/interface")
    def _event_router_db(self, message):
        self.update_router(message.data)


if __name__ == "__main__":
    FORMAT = "%(asctime)s - %(levelname)s - %(lineno)s - %(message)s"
    logging.basicConfig(level=0, format=FORMAT)
    _logger = logging.getLogger("sanji.route")

    route = IPRoute(connection=Mqtt())
    route.start()
