#!/usr/bin/env python
# -*- coding: UTF-8 -*-


import os
import sys
import logging
import unittest

from mock import patch

try:
    sys.path.append(os.path.dirname(os.path.realpath(__file__)) + '/../')
    from route import IPRoute
    from route import IPRouteError
except ImportError as e:
    print os.path.dirname(os.path.realpath(__file__)) + '/../'
    print sys.path
    print e
    print "Please check the python PATH for import test module. (%s)" \
        % __file__
    exit(1)

dirpath = os.path.dirname(os.path.realpath(__file__))


def mock_ip_addr_ifaddresses(iface):
    if "eth0" == iface:
        return {"mac": "78:ac:c0:c1:a8:fe",
                "link": True,
                "inet": [{
                    "broadcast": "192.168.31.255",
                    "ip": "192.168.31.36",
                    "netmask": "255.255.255.0",
                    "subnet": "192.168.31.0"}]}
    elif "eth1" == iface:
        return {"mac": "78:ac:c0:c1:a8:ff",
                "link": False,
                "inet": [{
                    "broadcast": "192.168.41.255",
                    "ip": "192.168.41.37",
                    "netmask": "255.255.255.0",
                    "subnet": "192.168.41.0"}]}
    elif "ppp0" == iface:
        return {"mac": "",
                "link": True,
                "inet": [{
                    "broadcast": "192.168.41.255",
                    "ip": "192.168.41.37",
                    "netmask": "255.255.255.0",
                    "subnet": "192.168.41.0"}]}
    else:
        raise ValueError


class TestIPRouteClass(unittest.TestCase):

    @patch.object(IPRoute, '_update_default')
    def setUp(self, mock_update_default):
        self.name = "route"
        self.path = os.path.abspath(os.path.dirname(__file__) + "/../")
        self.bundle = IPRoute(name=self.name, path=self.path)

    def tearDown(self):
        self.bundle = None
        try:
            os.remove("{}/data/{}.json".format(self.path, self.name))
        except OSError:
            pass

        try:
            os.remove("{}/data/{}.json.backup".format(self.path, self.name))
        except OSError:
            pass

    @patch("route.ip.addr.ifaddresses")
    @patch("route.ip.addr.interfaces")
    def test__list_interfaces(self, mock_interfaces, mock_ifaddresses):
        """
        list_interfaces: list the available interfaces
        """
        mock_interfaces.return_value = ["eth0", "eth1", "ppp0"]
        mock_ifaddresses.side_effect = mock_ip_addr_ifaddresses
        self.bundle._interfaces = {}
        self.bundle._interfaces["eth0"] = {
            "status": True,
            "wan": True
        }
        self.bundle._interfaces["ppp0"] = {
            "status": True,
            "wan": True
        }

        ifaces = self.bundle.list_interfaces()
        print(ifaces)
        self.assertEqual(2, len(ifaces))
        self.assertIn("eth0", ifaces)
        self.assertIn("ppp0", ifaces)

    @patch("route.ip.addr.interfaces")
    def test__list_interfaces__failed_get_ifaces(self, mock_interfaces):
        """
        list_interfaces: failed to list the available interfaces
        """
        mock_interfaces.side_effect = IOError

        ifaces = self.bundle.list_interfaces()
        self.assertEqual({}, ifaces)

    @patch("route.ip.addr.ifaddresses")
    @patch("route.ip.addr.interfaces")
    def test__list_interfaces__failed_get_status(self, mock_interfaces,
                                                 mock_ifaddresses):
        """
        list_interfaces: cannot get some interface's status
        """
        def mock_ip_addr_ifaddresses_ppp0_failed(iface):
            if "eth0" == iface:
                return {"mac": "78:ac:c0:c1:a8:fe",
                        "link": True,
                        "inet": [{
                            "broadcast": "192.168.31.255",
                            "ip": "192.168.31.36",
                            "netmask": "255.255.255.0",
                            "subnet": "192.168.31.0"}]}
            elif "eth1" == iface:
                return {"mac": "78:ac:c0:c1:a8:ff",
                        "link": False,
                        "inet": [{
                            "broadcast": "192.168.41.255",
                            "ip": "192.168.41.37",
                            "netmask": "255.255.255.0",
                            "subnet": "192.168.41.0"}]}
            else:
                raise ValueError
        self.bundle._interfaces["eth0"] = {
            "status": True,
            "wan": True
        }

        mock_interfaces.return_value = ["eth0", "eth1", "ppp0"]
        mock_ifaddresses.side_effect = mock_ip_addr_ifaddresses_ppp0_failed

        ifaces = self.bundle.list_interfaces()
        self.assertEqual(1, len(ifaces))
        self.assertIn("eth0", ifaces)

    @patch("route.ip.route.show")
    def test__get_default(self, mock_gateways):
        """
        get_default: get current default gateway
        """
        mock_gateways.return_value = [
            {"default": "192.168.3.254", "dev": "eth0"},
            {"src": "192.168.4.127",
             "dev": "eth1",
             "dest": "192.168.4.0/24"}
        ]

        default = self.bundle.get_default()
        self.assertEqual("eth0", default["interface"])
        self.assertEqual("192.168.3.254", default["gateway"])

    @patch("route.ip.route.show")
    def test__get_default__no_default(self, mock_gateways):
        """
        get_default: no current default gateway
        """
        mock_gateways.return_value = [
            {"src": "192.168.3.127",
             "dev": "eth0",
             "dest": "192.168.3.0/24"},
            {"src": "192.168.4.127",
             "dev": "eth1",
             "dest": "192.168.4.0/24"}]

        default = self.bundle.get_default()
        self.assertEqual({}, default)

    @patch("route.ip.route.delete")
    @patch("route.ip.route.add")
    def test__update_default(self, mock_ip_route_add, mock_ip_route_del):
        """
        _update_default: update the default gateway with both interface and
                         gateway
        """
        default = {}
        default["interface"] = "eth1"
        default["gateway"] = "192.168.4.254"

        try:
            self.bundle._update_default(default)
        except:
            self.fail("update_default raised exception unexpectedly!")

    @patch("route.ip.route.delete")
    @patch("route.ip.route.add")
    def test__update_default__with_iface(
            self, mock_ip_route_add, mock_ip_route_del):
        """
        _update_default: update the default gateway with interface
        """
        default = {}
        default["interface"] = "eth1"

        try:
            self.bundle._update_default(default)
        except:
            self.fail("_update_default raised exception unexpectedly!")

    @patch("route.ip.route.delete")
    @patch("route.ip.route.add")
    def test__update_default__with_gateway(self, mock_ip_route_add,
                                           mock_ip_route_del):
        """
        _update_default: update the default gateway with gateway
        """
        default = {}
        default["gateway"] = "192.168.4.254"

        try:
            self.bundle._update_default(default)
        except:
            self.fail("_update_default raised exception unexpectedly!")

    @patch("route.ip.route.delete")
    @patch("route.ip.route.add")
    def test__update_default__failed(self, mock_ip_route_add,
                                     mock_ip_route_del):
        """
        _update_default: failed to update the default gateway
        """
        mock_ip_route_add.side_effect = IOError
        default = {}
        default["gateway"] = "192.168.4.254"

        with self.assertRaises(IOError):
            self.bundle._update_default(default)

    @patch("route.ip.route.delete")
    def test__update_default__delete(self, mock_ip_route_del):
        """
        _update_default: delete the default gateway
        """
        default = {}

        try:
            self.bundle._update_default(default)
        except Exception as e:
            print(str(e))
            self.fail("_update_default raised exception unexpectedly!")

    @patch("route.ip.route.delete")
    def test__update_default__delete_failed(self, mock_ip_route_del):
        """
        _update_default: failed delete the default gateway
        """
        mock_ip_route_del.side_effect = IOError
        default = {}

        with self.assertRaises(IOError):
            self.bundle._update_default(default)

    @patch.object(IPRoute, "list_interfaces")
    def test__try_update_default__no_iface(self, mock_list_interfaces):
        """
        try_update_default: no interfaces
        """
        mock_list_interfaces.return_value = []

        with self.assertRaises(IPRouteError):
            self.bundle._try_update_default(self.bundle.model.db)

    @patch.object(IPRoute, "_update_default")
    @patch.object(IPRoute, "get_default")
    @patch.object(IPRoute, "list_interfaces")
    def test__try_update_default__by_default(
            self,
            mock_list_interfaces,
            mock_get_default,
            mock_update_default):
        """
        try_update_default: update by default
        """
        mock_list_interfaces.return_value = ["eth0", "eth1", "wwan0"]
        mock_get_default.return_value = {
            "interface": "eth1",
            "gateway": "192.168.4.254"
        }

        self.bundle._interfaces = {
            "eth0": {
                "status": True,
                "wan": True,
                "gateway": "192.168.3.254"
            },
            "eth1": {
                "status": True,
                "wan": False,
                "gateway": "192.168.4.254"
            }
        }

        routes = ["eth0", "eth1"]

        self.bundle._try_update_default(routes)

        default = self.bundle._interfaces["eth0"]
        default["interface"] = "eth0"
        mock_update_default.assert_called_once_with(default)

    @patch.object(IPRoute, "_update_default")
    @patch.object(IPRoute, "get_default")
    @patch.object(IPRoute, "list_interfaces")
    def test__try_update_default__by_default_with_current_value(
            self,
            mock_list_interfaces,
            mock_get_default,
            mock_update_default):
        """
        try_update_default: update by default (same with current setting)
        """
        mock_list_interfaces.return_value = ["eth0", "eth1", "wwan0"]
        mock_get_default.return_value = {
            "interface": "eth0",
            "gateway": "192.168.3.254"
        }

        self.bundle._interfaces = {
            "eth0": {
                "status": True,
                "wan": True,
                "gateway": "192.168.3.254"
            },
            "eth1": {
                "status": True,
                "wan": True,
                "gateway": "192.168.4.254"
            }
        }

        routes = ["eth0", "eth1"]

        self.bundle._try_update_default(routes)
        mock_update_default.assert_called_once()

    @patch.object(IPRoute, "_update_default")
    @patch.object(IPRoute, "get_default")
    @patch.object(IPRoute, "list_interfaces")
    def test__try_update_default__by_secondary(
            self,
            mock_list_interfaces,
            mock_get_default,
            mock_update_default):
        """
        try_update_default: update by secondary
        """
        # arrange
        mock_list_interfaces.return_value = ["eth1", "wwan0"]
        mock_get_default.return_value = {
            "interface": "wwan0",
            "gateway": "192.168.4.254"
        }

        self.bundle._interfaces = {
            "eth0": {
                "status": False,
                "wan": True,
                "gateway": "192.168.3.254"
            },
            "eth1": {
                "status": True,
                "wan": True,
                "gateway": "192.168.4.254"
            },
            "wwan0": {
                "status": True,
                "wan": True,
                "gateway": "192.168.5.254"
            }
        }

        routes = ["eth0", "wwan0"]

        # act
        self.bundle._try_update_default(routes)

        # assert
        default = self.bundle._interfaces["wwan0"]
        default["interface"] = "wwan0"
        mock_update_default.assert_called_once_with(default)

    @patch.object(IPRoute, "_update_default")
    @patch.object(IPRoute, "list_interfaces")
    def test__try_update_default__delete(
            self,
            mock_list_interfaces,
            mock_update_default):
        """
        try_update_default: delete default gateway
        """
        mock_list_interfaces.return_value = ["eth1"]

        routes = ["wwan0", "eth0"]

        self.bundle._try_update_default(routes)
        mock_update_default.assert_called_once_with({})

    @patch.object(IPRoute, '_update_default')
    def test__update_iface_db__update_interface(
            self, mock_update_default):
        """
        update_router: update router info by interface
        """
        # arrange
        self.bundle._interfaces = {
            "eth0": {
                "status": True,
                "wan": True,
                "gateway": "192.168.31.254"
            },
            "eth1": {
                "status": True,
                "wan": True,
                "gateway": "192.168.4.254"
            }
        }
        iface = {"name": "eth1", "gateway": "192.168.41.254"}

        # act
        self.bundle.update_iface_db(iface)

        # assert
        eth0 = {
            "eth0": {
                "status": True,
                "wan": True,
                "gateway": "192.168.31.254"
            }
        }
        eth1 = {
            "eth1": {
                "status": True,
                "wan": True,
                "gateway": "192.168.41.254"
            }
        }
        self.assertEqual(2, len(self.bundle._interfaces))
        self.assertEqual(eth0["eth0"], self.bundle._interfaces["eth0"])
        self.assertEqual(eth1["eth1"], self.bundle._interfaces["eth1"])

    @patch.object(IPRoute, '_update_default')
    def test__update_iface_db__add_interface_with_gateway(
            self, mock_update_default):
        """
        update_router: add a new interface with gateway
        """
        # arrange
        self.bundle._interfaces = {
            "eth0": {
                "status": True,
                "wan": True,
                "gateway": "192.168.31.254"
            }
        }
        iface = {"name": "eth1", "gateway": "192.168.41.254"}

        # act
        self.bundle.update_iface_db(iface)

        # assert
        eth0 = {
            "eth0": {
                "status": True,
                "wan": True,
                "gateway": "192.168.31.254"
            }
        }
        eth1 = {
            "eth1": {
                "status": True,
                "wan": True,
                "gateway": "192.168.41.254"
            }
        }
        self.assertEqual(2, len(self.bundle._interfaces))
        self.assertEqual(eth0["eth0"], self.bundle._interfaces["eth0"])
        self.assertEqual(eth1["eth1"], self.bundle._interfaces["eth1"])

    @patch.object(IPRoute, '_update_default')
    def test__update_iface_db__add_interface_without_gateway(
            self, mock_update_default):
        """
        update_router: add a new interface without gateway
        """
        # arrange
        self.bundle._interfaces = {
            "eth0": {
                "status": True,
                "wan": True,
                "gateway": "192.168.31.254"
            }
        }
        iface = {"name": "eth1"}

        # act
        self.bundle.update_iface_db(iface)

        # assert
        eth0 = {
            "eth0": {
                "status": True,
                "wan": True,
                "gateway": "192.168.31.254"
            }
        }
        eth1 = {
            "eth1": {
                "status": True,
                "wan": True
            }
        }
        self.assertEqual(2, len(self.bundle._interfaces))
        self.assertEqual(eth0["eth0"], self.bundle._interfaces["eth0"])
        self.assertEqual(eth1["eth1"], self.bundle._interfaces["eth1"])

    @patch.object(IPRoute, "get_default")
    @patch.object(IPRoute, 'try_update_default')
    def test__update_iface_db__update_default(
            self, mock_try_update_default, mock_get_default):
        """
        update_router: default gateway should also be updated
        """
        # arrange
        mock_get_default.return_value = {
            "interface": "eth0",
            "gateway": "192.168.3.254"
        }
        self.bundle._interfaces = {
            "eth0": {
                "status": True,
                "wan": True,
                "gateway": "192.168.3.254"
            },
            "eth1": {
                "status": True,
                "wan": True,
                "gateway": "192.168.4.254"
            }
        }
        iface = {"name": "eth0", "gateway": "192.168.31.254"}

        # act
        self.bundle.update_iface_db(iface)

        # assert
        eth0 = {
            "eth0": {
                "status": True,
                "wan": True,
                "gateway": "192.168.31.254"
            }
        }
        eth1 = {
            "eth1": {
                "status": True,
                "wan": True,
                "gateway": "192.168.4.254"
            }
        }
        self.assertEqual(2, len(self.bundle._interfaces))
        self.assertEqual(eth0["eth0"], self.bundle._interfaces["eth0"])
        self.assertEqual(eth1["eth1"], self.bundle._interfaces["eth1"])
        mock_try_update_default.assert_called_once_with(self.bundle.model.db)


if __name__ == "__main__":
    FORMAT = '%(asctime)s - %(levelname)s - %(lineno)s - %(message)s'
    logging.basicConfig(level=20, format=FORMAT)
    logger = logging.getLogger('IPRoute Test')
    unittest.main()
