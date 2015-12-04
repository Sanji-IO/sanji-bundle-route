#!/usr/bin/env python
# -*- coding: UTF-8 -*-


import os
import sys
import logging
import unittest

from mock import patch
from mock import Mock
from sanji.connection.mockup import Mockup
from sanji.message import Message

try:
    sys.path.append(os.path.dirname(os.path.realpath(__file__)) + '/../')
    from route import IPRoute
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
                "link": 1,
                "inet": [{
                    "broadcast": "192.168.31.255",
                    "ip": "192.168.31.36",
                    "netmask": "255.255.255.0",
                    "subnet": "192.168.31.0"}]}
    elif "eth1" == iface:
        return {"mac": "78:ac:c0:c1:a8:ff",
                "link": 0,
                "inet": [{
                    "broadcast": "192.168.41.255",
                    "ip": "192.168.41.37",
                    "netmask": "255.255.255.0",
                    "subnet": "192.168.41.0"}]}
    elif "ppp0" == iface:
        return {"mac": "",
                "link": 1,
                "inet": [{
                    "broadcast": "192.168.41.255",
                    "ip": "192.168.41.37",
                    "netmask": "255.255.255.0",
                    "subnet": "192.168.41.0"}]}
    else:
        raise ValueError


class TestIPRouteClass(unittest.TestCase):

    @patch.object(IPRoute, 'update_default')
    def setUp(self, mock_update_default):
        self.name = "route"
        self.bundle = IPRoute(connection=Mockup())

    def tearDown(self):
        self.bundle.stop()
        self.bundle = None
        try:
            os.remove("%s/data/%s.json" % (dirpath, self.name))
        except OSError:
            pass

        try:
            os.remove("%s/data/%s.json.backup" % (dirpath, self.name))
        except OSError:
            pass

    @patch.object(IPRoute, 'update_default')
    def test__init__no_conf(self, mock_update_default):
        """
        init: no configuration file
        """
        with self.assertRaises(IOError):
            with patch("route.ModelInitiator") as mock_modelinit:
                mock_modelinit.side_effect = IOError
                self.bundle.init()

    def test__load__current_conf(self):
        """
        load: load current configuration
        """
        self.bundle.load(dirpath)
        self.assertEqual("eth0", self.bundle.model.db["default"])

    def test__load__backup_conf(self):
        """
        load: load backup configuration
        """
        os.remove("%s/data/%s.json" % (dirpath, self.name))
        self.bundle.load(dirpath)
        self.assertEqual("eth0", self.bundle.model.db["default"])

    def test__load__no_conf(self):
        """
        load: cannot load any configuration
        """
        with self.assertRaises(Exception):
            self.bundle.load("%s/mock" % dirpath)

    def test__save(self):
        """
        save
        """
        # Already tested in init()
        pass

    @patch("route.ip.addr.ifaddresses")
    @patch("route.ip.addr.interfaces")
    def test__list_interfaces(self, mock_interfaces, mock_ifaddresses):
        """
        list_interfaces: list the available interfaces
        """
        mock_interfaces.return_value = ["eth0", "eth1", "ppp0"]
        mock_ifaddresses.side_effect = mock_ip_addr_ifaddresses

        ifaces = self.bundle.list_interfaces()
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
                        "link": 1,
                        "inet": [{
                            "broadcast": "192.168.31.255",
                            "ip": "192.168.31.36",
                            "netmask": "255.255.255.0",
                            "subnet": "192.168.31.0"}]}
            elif "eth1" == iface:
                return {"mac": "78:ac:c0:c1:a8:ff",
                        "link": 0,
                        "inet": [{
                            "broadcast": "192.168.41.255",
                            "ip": "192.168.41.37",
                            "netmask": "255.255.255.0",
                            "subnet": "192.168.41.0"}]}
            else:
                raise ValueError

        mock_interfaces.return_value = ["eth0", "eth1", "ppp0"]
        mock_ifaddresses.side_effect = mock_ip_addr_ifaddresses_ppp0_failed

        ifaces = self.bundle.list_interfaces()
        self.assertEqual(1, len(ifaces))
        self.assertIn("eth0", ifaces)

    @patch("route.netifaces.gateways")
    def test__get_default(self, mock_gateways):
        """
        get_default: get current default gateway
        """
        mock_gateways.return_value = {
            'default': {2: ('192.168.3.254', 'eth0')},
            2: [('192.168.3.254', 'eth0', True)]}

        default = self.bundle.get_default()
        self.assertEqual("eth0", default["interface"])
        self.assertEqual("192.168.3.254", default["gateway"])

    @patch("route.netifaces.gateways")
    def test__get_default__no_default(self, mock_gateways):
        """
        get_default: no current default gateway
        """
        mock_gateways.return_value = {'default': {}}

        default = self.bundle.get_default()
        self.assertEqual({}, default)

    @patch.object(IPRoute, "update_wan_info")
    @patch("route.ip.route.delete")
    @patch("route.ip.route.add")
    def test__update_default(self, mock_ip_route_add, mock_ip_route_del,
                             mock_update_wan_info):
        """
        update_default: update the default gateway with both interface and
                        gateway
        """
        default = {}
        default["interface"] = "eth1"
        default["gateway"] = "192.168.4.254"

        try:
            self.bundle.update_default(default)
        except:
            self.fail("update_default raised exception unexpectedly!")

    @patch.object(IPRoute, "update_wan_info")
    @patch("route.ip.route.delete")
    @patch("route.ip.route.add")
    def test__update_default__with_iface(self, mock_ip_route_add,
                                         mock_ip_route_del, mock_update_wan_info):
        """
        update_default: update the default gateway with interface
        """
        default = {}
        default["interface"] = "eth1"

        try:
            self.bundle.update_default(default)
        except:
            self.fail("update_default raised exception unexpectedly!")

    @patch("route.ip.route.delete")
    @patch("route.ip.route.add")
    def test__update_default__with_gateway(self, mock_ip_route_add,
                                           mock_ip_route_del):
        """
        update_default: update the default gateway with gateway
        """
        default = {}
        default["gateway"] = "192.168.4.254"

        try:
            self.bundle.update_default(default)
        except:
            self.fail("update_default raised exception unexpectedly!")

    @patch("route.ip.route.delete")
    @patch("route.ip.route.add")
    def test__update_default__failed(self, mock_ip_route_add,
                                     mock_ip_route_del):
        """
        update_default: failed to update the default gateway
        """
        mock_ip_route_add.side_effect = IOError
        default = {}
        default["gateway"] = "192.168.4.254"

        with self.assertRaises(IOError):
            self.bundle.update_default(default)

    @patch("route.ip.route.delete")
    def test__update_default__delete(self, mock_ip_route_del):
        """
        update_default: delete the default gateway
        """
        default = {}

        try:
            self.bundle.update_default(default)
        except:
            self.fail("update_default raised exception unexpectedly!")

    @patch("route.ip.route.delete")
    def test__update_default__delete_failed(self, mock_ip_route_del):
        """
        update_default: failed delete the default gateway
        """
        mock_ip_route_del.side_effect = IOError
        default = {}

        with self.assertRaises(IOError):
            self.bundle.update_default(default)

    @patch.object(IPRoute, "list_interfaces")
    def test__try_update_default__no_iface(self, mock_list_interfaces):
        """
        try_update_default: no interfaces
        """
        mock_list_interfaces.return_value = []

        with self.assertRaises(ValueError):
            self.bundle.try_update_default(self.bundle.model.db)

    @patch.object(IPRoute, "update_default")
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

        self.bundle.interfaces = [
            {
                "interface": "eth0",
                "gateway": "192.168.3.254"
            },
            {
                "interface": "eth1",
                "gateway": "192.168.4.254"
            }
        ]

        routes = {}
        routes["default"] = "eth0"
        routes["secondary"] = "eth1"

        self.bundle.try_update_default(routes)
        mock_update_default.assert_called_once_with(self.bundle.interfaces[0])

    @patch.object(IPRoute, "update_default")
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

        self.bundle.interfaces = [
            {
                "interface": "eth0",
                "gateway": "192.168.3.254"
            },
            {
                "interface": "eth1",
                "gateway": "192.168.4.254"
            }
        ]

        routes = {}
        routes["default"] = "eth0"
        routes["secondary"] = "eth1"

        self.bundle.try_update_default(routes)
        self.assertTrue(not mock_update_default.called)

    @patch.object(IPRoute, "update_default")
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

        self.bundle.interfaces = [
            {
                "interface": "eth0",
                "gateway": "192.168.3.254"
            },
            {
                "interface": "eth1",
                "gateway": "192.168.4.254"
            },
            {
                "interface": "wwan0",
                "gateway": "192.168.5.254"
            }
        ]

        routes = {}
        routes["default"] = "eth0"
        routes["secondary"] = "wwan0"

        # act
        self.bundle.try_update_default(routes)

        # assert
        mock_update_default.assert_called_once_with(self.bundle.interfaces[2])

    @patch.object(IPRoute, "update_default")
    @patch.object(IPRoute, "list_interfaces")
    def test__try_update_default__delete(
            self,
            mock_list_interfaces,
            mock_update_default):
        """
        try_update_default: delete default gateway
        """
        mock_list_interfaces.return_value = ["eth1"]

        routes = {}
        routes["default"] = "wwan0"
        routes["secondary"] = "eth0"

        self.bundle.try_update_default(routes)
        mock_update_default.assert_called_once_with({})

    @patch.object(IPRoute, 'update_default')
    def test__update_router__update_interface(
            self, mock_update_default):
        """
        update_router: update router info by interface
        """
        # arrange
        self.bundle.interfaces = [
            {"interface": "eth0", "gateway": "192.168.31.254"},
            {"interface": "eth1", "gateway": "192.168.4.254"}]
        iface = {"name": "eth1", "gateway": "192.168.41.254"}

        # act
        self.bundle.update_router(iface)

        # assert
        self.assertEqual(2, len(self.bundle.interfaces))
        self.assertIn({"interface": "eth0", "gateway": "192.168.31.254"},
                      self.bundle.interfaces)
        self.assertIn({"interface": "eth1", "gateway": "192.168.41.254"},
                      self.bundle.interfaces)

    @patch.object(IPRoute, 'update_default')
    def test__update_router__add_interface_with_gateway(
            self, mock_update_default):
        """
        update_router: add a new interface with gateway
        """
        # arrange
        self.bundle.interfaces = [
            {"interface": "eth0", "gateway": "192.168.31.254"}]
        iface = {"name": "eth1", "gateway": "192.168.41.254"}

        # act
        self.bundle.update_router(iface)

        # assert
        self.assertEqual(2, len(self.bundle.interfaces))
        self.assertIn({"interface": "eth0", "gateway": "192.168.31.254"},
                      self.bundle.interfaces)
        self.assertIn({"interface": "eth1", "gateway": "192.168.41.254"},
                      self.bundle.interfaces)

    @patch.object(IPRoute, 'update_default')
    def test__update_router__add_interface_without_gateway(
            self, mock_update_default):
        """
        update_router: add a new interface without gateway
        """
        # arrange
        self.bundle.interfaces = [
            {"interface": "eth0", "gateway": "192.168.31.254"}]
        iface = {"name": "eth1"}

        # act
        self.bundle.update_router(iface)

        # assert
        self.assertEqual(2, len(self.bundle.interfaces))
        self.assertIn({"interface": "eth0", "gateway": "192.168.31.254"},
                      self.bundle.interfaces)
        self.assertIn({"interface": "eth1"},
                      self.bundle.interfaces)

    @patch.object(IPRoute, "get_default")
    @patch.object(IPRoute, 'try_update_default')
    def test__update_router__update_default(
            self, mock_try_update_default, mock_get_default):
        """
        update_router: default gateway should also be updated
        """
        # arrange
        mock_get_default.return_value = {
            "interface": "eth0",
            "gateway": "192.168.3.254"
        }
        self.bundle.interfaces = [
            {"interface": "eth0", "gateway": "192.168.3.254"},
            {"interface": "eth1", "gateway": "192.168.4.254"}]
        iface = {"name": "eth0", "gateway": "192.168.31.254"}

        # act
        self.bundle.update_router(iface)

        # assert
        self.assertEqual(2, len(self.bundle.interfaces))
        self.assertIn({"interface": "eth0", "gateway": "192.168.31.254"},
                      self.bundle.interfaces)
        self.assertIn({"interface": "eth1", "gateway": "192.168.4.254"},
                      self.bundle.interfaces)
        mock_try_update_default.assert_called_once_with(self.bundle.model.db)

    @patch.object(IPRoute, "update_default")
    def test__set_default__default(self, mock_update_default):
        """
        set_default: update default gateway
        """
        # arrange
        self.bundle.model.db["default"] = "eth1"
        default = {
            "interface": "eth0",
            "gateway": "192.168.3.254"
        }

        # act
        self.bundle.set_default(default)

        # assert
        self.assertEqual(self.bundle.model.db, {"default": "eth0"})
        mock_update_default.assert_called_once_with(default)

    @patch.object(IPRoute, "try_update_default")
    @patch.object(IPRoute, "update_default")
    def test__set_default__update_default_failed(
            self,
            mock_update_default,
            mock_try_update_default):
        """
        set_default: update default gateway failed
        """
        # arrange
        mock_update_default.side_effect = IOError
        self.bundle.model.db["default"] = "eth1"
        default = {
            "interface": "eth0",
            "gateway": "192.168.3.254"
        }

        # act
        with self.assertRaises(IOError):
            self.bundle.set_default(default)

        # assert
        self.assertEqual(self.bundle.model.db, {"default": "eth0"})
        mock_update_default.assert_called_once_with(default)
        mock_try_update_default.assert_called_once_with(self.bundle.model.db)

    @patch.object(IPRoute, "try_update_default")
    @patch.object(IPRoute, "update_default")
    def test__set_default__update_default_and_recovery_failed(
            self,
            mock_update_default,
            mock_try_update_default):
        """
        set_default: update default gateway failed and recovery failed
        """
        # arrange
        mock_update_default.side_effect = IOError
        mock_try_update_default.side_effect = IOError
        self.bundle.model.db["default"] = "eth1"
        default = {
            "interface": "eth0",
            "gateway": "192.168.3.254"
        }

        # act
        with self.assertRaises(IOError):
            self.bundle.set_default(default)

        # assert
        self.assertEqual(self.bundle.model.db, {"default": "eth0"})
        mock_update_default.assert_called_once_with(default)
        mock_try_update_default.assert_called_once_with(self.bundle.model.db)

    def test__set_default__secondary(self):
        """
        set_default: update secondary default gateway
        """
        # arrange
        self.bundle.model.db["default"] = "eth1"
        default = {
            "interface": "eth0",
            "gateway": "192.168.3.254"
        }

        # act
        self.bundle.set_default(default, False)

        # assert
        self.assertEqual(self.bundle.model.db,
                         {"default": "eth1", "secondary": "eth0"})

    @patch("route.ip.route.delete")
    def test__set_default__clear(self, mock_ip_route_del):
        """
        set_default: clear default gateway
        """
        # arrange
        self.bundle.model.db["default"] = "eth1"
        default = {}

        # act
        self.bundle.set_default(default)

        # assert
        self.assertEqual(self.bundle.model.db, {"default": ""})
        mock_ip_route_del.assert_called_once_with("default")

    @patch.object(IPRoute, "update_default")
    def test__set_default__no_change(self, mock_update_default):
        """
        set_default: default gateway doesn't change
        """
        # arrange
        self.bundle.model.db["default"] = "eth1"
        default = {"gateway": "192.168.3.254"}

        # act
        self.bundle.set_default(default)

        # assert
        self.assertEqual(self.bundle.model.db, {"default": "eth1"})

    @patch.object(IPRoute, "update_default")
    def test__set_router_db__add(self, mock_update_default):
        """
        set_router_db: add one interface's router info to database
        """
        # arrange
        iface = {"name": "eth0", "gateway": "192.168.3.127"}
        message = Message({"data": iface})
        mock_func = Mock(code=200, data=None)

        # act
        self.bundle.set_router_db(message=message, response=mock_func)

        # assert
        self.assertEqual(mock_func.call_args_list[0][1]["data"], iface)


if __name__ == "__main__":
    FORMAT = '%(asctime)s - %(levelname)s - %(lineno)s - %(message)s'
    logging.basicConfig(level=20, format=FORMAT)
    logger = logging.getLogger('IPRoute Test')
    unittest.main()
