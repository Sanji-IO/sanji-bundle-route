#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import os
import logging
from sanji.core import Sanji
from sanji.core import Route
from sanji.connection.mqtt import Mqtt
from sanji.model_initiator import ModelInitiator
from voluptuous import Schema
from voluptuous import Any, Extra, Optional

import ip


# TODO: logger should be defined in sanji package?
logger = logging.getLogger()


class IPRoute(Sanji):
    """
    A model to handle IP Route configuration.

    Attributes:
        model: database with json format.
    """
    def init(self, *args, **kwargs):
        try:  # pragma: no cover
            self.bundle_env = kwargs["bundle_env"]
        except KeyError:
            self.bundle_env = os.getenv("BUNDLE_ENV", "debug")

        path_root = os.path.abspath(os.path.dirname(__file__))
        if self.bundle_env == "debug":  # pragma: no cover
            path_root = "%s/tests" % path_root

        try:
            self.load(path_root)
        except:
            self.stop()
            raise IOError("Cannot load any configuration.")

        self.cellular = None

    def load(self, path):
        """
        Load the configuration. If configuration is not installed yet,
        initialise them with default value.

        Args:
            path: Path for the bundle, the configuration should be located
                under "data" directory.
        """
        self.model = ModelInitiator("route", path, backup_interval=-1)
        if None == self.model.db:
            raise IOError("Cannot load any configuration.")
        self.save()

    def save(self):
        """
        Save and backup the configuration.
        """
        self.model.save_db()
        self.model.backup_db()

    def cellular_connected(self, name, up=True):
        """
        If cellular is connected, the default gateway should be set to
        cellular interface.

        Args:
            name: cellular's interface name
        """
        default = dict()
        if up:
            self.cellular = name
            default["interface"] = self.cellular
            self.update_default(default)
        else:
            self.cellular = None
            if name == self.model.db["interface"]:
                self.update_default(default)

    def list_interfaces(self):
        """
        List available interfaces.
        """
        # retrieve all interfaces
        try:
            ifaces = ip.addr.interfaces()
        except:
            return None
        """
        except Exception as e:
            raise e
        """

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

    def update_default(self, default):
        """
        Update default gateway. If updated failed, should recover to previous
        one.

        Args:
            default: dict format with "interface" required and "gateway"
                     optional.
        """
        # change the default gateway
        if "interface" in default and default["interface"]:
            ifaces = self.list_interfaces()
            if default["interface"] not in ifaces:
                raise ValueError("Interface should be UP.")
            # FIXME: how to determine a interface is produced by cellular
            # elif any("ppp" in s for s in ifaces):
            elif self.cellular:
                raise ValueError("Cellular is connected, the default gateway"
                                 "cannot be changed.")

            try:
                ip.route.delete("default")
                if "gateway" in default:
                    ip.route.add("default", default["interface"],
                                 default["gateway"])
                else:
                    ip.route.add("default", default["interface"])
            except Exception as e:
                raise e
            self.model.db["interface"] = default["interface"]

        # delete the default gateway
        else:
            try:
                ip.route.delete("default")
            except Exception as e:
                raise e
            if "interface" in self.model.db:
                self.model.db.pop("interface")

        self.save()

    @Route(methods="get", resource="/network/routes/interfaces")
    def get_interfaces(self, message, response):
        """
        Get available interfaces.
        """
        data = self.list_interfaces()
        return response(data=data)

    @Route(methods="get", resource="/network/routes/default")
    def get_default(self, message, response):
        """
        Get default gateway.
        """
        return response(data=self.model.db)

    put_default_schema = Schema({
        Optional("interface"): Any(str, unicode),
        Extra: object})

    @Route(methods="put", resource="/network/routes/default")
    def put_default(self, message, response, schema=put_default_schema):
        """
        Update the default gateway, delete default gateway if data is None or
        empty.
        """
        # TODO: should be removed when schema worked for unittest
        try:
            IPRoute.put_default_schema(message.data)
        except Exception as e:
            return response(code=400,
                            data={"message": "Invalid input: %s." % e})

        # retrieve the default gateway
        rules = ip.route.show()
        default = None
        for rule in rules:
            if "default" in rule:
                default = rule
                break

        try:
            self.update_default(message.data)
            return response(data=self.model.db)
        except Exception as e:
            # recover the previous default gateway if any
            try:
                if default:
                    default["interface"] = default["dev"]
                    default["gateway"] = default["default"]
                    self.update_default(default)
            except:
                logger.info("Failed to recover the default gateway.")
            logger.info("Update default gateway failed: %s" % e)
            return response(code=404,
                            data={"message":
                                  "Update default gateway failed: %s"
                                  % e})

    @Route(methods="put", resource="/network/ethernets/:id")
    def hook_put_ethernet_by_id(self, message, response):
        # check if the default gateway need to be modified
        if message.data["name"] == self.model.db["interface"]:
            default = dict()
            default["interface"] = message.data["name"]
            if "gateway" in message.data:
                default["gateway"] = message.data["gateway"]
            self.update_default(default)
            return response(data=self.model.db)
        return response(data=self.model.db)

    @Route(methods="put", resource="/network/ethernets")
    def hook_put_ethernets(self, message, response):
        for iface in message.data:
            if iface["name"] == self.model.db["interface"]:
                default = dict()
                default["interface"] = iface["name"]
                if "gateway" in iface:
                    default["gateway"] = iface["gateway"]
                self.update_default(default)
                return response(data=self.model.db)
        return response(data=self.model.db)

    ''' Event can only received by view...
    @Route(methods="put", resource="/network/cellulars")
    def event_put_cellulars(self, message, response):
        """
        Listen the cellular's event for interface connected or disconnected.
        """
        pass
    '''


if __name__ == "__main__":
    FORMAT = "%(asctime)s - %(levelname)s - %(lineno)s - %(message)s"
    logging.basicConfig(level=0, format=FORMAT)
    logger = logging.getLogger("IP Route")

    route = IPRoute(connection=Mqtt())
    route.start()
