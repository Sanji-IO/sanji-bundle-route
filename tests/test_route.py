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
        with self.assertRaises(IOError):
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

    @patch("route.ip.route.delete")
    @patch("route.ip.route.add")
    def test__update_default(self, mock_ip_route_add, mock_ip_route_del):
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

    @patch("route.ip.route.delete")
    @patch("route.ip.route.add")
    def test__update_default__with_iface(self, mock_ip_route_add,
                                         mock_ip_route_del):
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

    def test__try_update_default(self):
        """
        try_update_default: no interfaces
        try_update_default: update by default
        try_update_default: update by secondary
        try_update_default: delete default gateway
        """
        pass

    @patch("route.ip.route.add")
    @patch("route.ip.route.delete")
    @patch.object(IPRoute, 'list_interfaces')
    def test__update_default__add_without_gateway(
            self, mock_list_interfaces, mock_route_delete, mock_route_add):
        mock_list_interfaces.return_value = ["eth0", "eth1"]

        # case: add the default gateway
        default = dict()
        default["interface"] = "eth1"
        self.bundle.update_default(default)
        self.assertIn("eth1", self.bundle.model.db["default"])

    @patch("route.ip.route.add")
    @patch("route.ip.route.delete")
    @patch.object(IPRoute, 'list_interfaces')
    def test__update_default__add_with_gateway(
            self, mock_list_interfaces, mock_route_delete, mock_route_add):
        mock_list_interfaces.return_value = ["eth0", "eth1"]

        # case: add the default gateway
        default = dict()
        default["interface"] = "eth1"
        default["gateway"] = "192.168.4.254"
        self.bundle.update_default(default)
        self.assertIn("eth1", self.bundle.model.db["default"])

    @patch.object(IPRoute, 'list_interfaces')
    def test__update_default__add_failed_iface_down(
            self, mock_list_interfaces):
        mock_list_interfaces.return_value = ["eth0"]

        # case: fail to add the default gateway when indicated interface is
        # down
        default = dict()
        default["interface"] = "eth1"
        default["gateway"] = "192.168.4.254"
        with self.assertRaises(ValueError):
            self.bundle.update_default(default)
        self.assertIn("default", self.bundle.model.db)

    @patch.object(IPRoute, 'list_interfaces')
    def test__update_default__add_failed_cellular_connected(
            self, mock_list_interfaces):
        mock_list_interfaces.return_value = ["eth0", "ppp0"]
        self.bundle.cellular = "ppp0"

        # case: fail to add the default gateway when ppp is connected
        default = dict()
        default["interface"] = "eth0"
        default["gateway"] = "192.168.3.254"
        with self.assertRaises(ValueError):
            self.bundle.update_default(default)

    @patch("route.ip.route.add")
    @patch("route.ip.route.delete")
    @patch.object(IPRoute, 'list_interfaces')
    def test__update_default__add_failed(
            self, mock_list_interfaces, mock_route_delete, mock_route_add):
        mock_list_interfaces.return_value = ["eth0", "eth1"]
        mock_route_add.side_effect = ValueError

        # case: fail to add the default gateway
        default = dict()
        default["interface"] = "eth0"
        default["gateway"] = "192.168.3.254"
        with self.assertRaises(ValueError):
            self.bundle.update_default(default)

    @patch.object(IPRoute, 'update_default')
    def test__update_router__update_interface(
            self, mock_update_default):
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

    @patch.object(IPRoute, 'update_default')
    def test__update_router__update_default(
            self, mock_update_default):
        # arrange
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

    @patch("route.ip.addr.ifaddresses")
    @patch("route.ip.addr.interfaces")
    def test__get_interfaces(self, mock_interfaces, mock_ifaddresses):
        mock_interfaces.return_value = ["eth0", "eth1", "ppp0"]
        mock_ifaddresses.side_effect = mock_ip_addr_ifaddresses

        # case: get supported interface list
        message = Message({"data": {}, "query": {}, "param": {}})

        def resp(code=200, data=None):
            self.assertEqual(200, code)
            self.assertEqual(2, len(data))
            self.assertIn("eth0", data)
            self.assertIn("ppp0", data)
        self.bundle._get_interfaces(message=message, response=resp, test=True)

    @patch("route.ip.addr.interfaces")
    def test__get_interfaces__failed(self, mock_interfaces):
        mock_interfaces.side_effect = ValueError

        # case: fail to get supported interface list
        message = Message({"data": {}, "query": {}, "param": {}})

        def resp(code=404, data=None):
            self.assertEqual(404, code)
            self.assertEqual({}, data)
        self.bundle._get_interfaces(message=message, response=resp, test=True)

    @patch.object(IPRoute, 'get_default')
    def test___get_default__match(self, mock_get_default):
        mock_get_default.return_value = {
            "interface": "eth0", "gateway": "192.168.3.254"}

        # case: get default gateway info.
        message = Message({"data": {}, "query": {}, "param": {}})

        def resp(code=200, data=None):
            self.assertEqual(200, code)
            self.assertEqual("eth0", data["interface"])
            self.assertEqual("192.168.3.254", data["gateway"])
        self.bundle._get_default(message=message, response=resp, test=True)

    @patch.object(IPRoute, 'get_default')
    def test___get_default__different(self, mock_get_default):
        mock_get_default.return_value = {
            "interface": "eth1", "gateway": "192.168.4.254"}

        # case: get current default gateway info.
        message = Message({"data": {}, "query": {}, "param": {}})

        def resp(code=200, data=None):
            self.assertEqual(200, code)
            self.assertEqual("eth1", data["interface"])
        self.bundle._get_default(message=message, response=resp, test=True)

    @patch.object(IPRoute, 'get_default')
    def test___get_default__empty(self, mock_get_default):
        mock_get_default.return_value = {}
        self.bundle.model.db = {}

        # case: no default gateway set
        message = Message({"data": {}, "query": {}, "param": {}})

        def resp(code=200, data=None):
            self.assertEqual(200, code)
            self.assertEqual({}, data)
        self.bundle._get_default(message=message, response=resp, test=True)

    def test__put_default__none(self):
        # case: None data is not allowed
        message = Message({"data": None, "query": {}, "param": {}})

        def resp(code=200, data=None):
            self.assertEqual(400, code)
        self.bundle._put_default(message=message, response=resp, test=True)

    @patch.object(IPRoute, 'update_default')
    def test__put_default__delete(self, mock_update_default):
        # case: delete the default gateway
        message = Message({"data": {}, "query": {}, "param": {}})

        def resp(code=200, data=None):
            self.assertEqual(200, code)
        self.bundle._put_default(message=message, response=resp, test=True)

    @patch.object(IPRoute, 'update_default')
    def test__put_default__delete_with_empty_iface(self, mock_update_default):
        # case: delete the default gateway
        message = Message(
            {"data": {"interface": ""}, "query": {}, "param": {}})

        def resp(code=200, data=None):
            self.assertEqual(200, code)
        self.bundle._put_default(message=message, response=resp, test=True)

    @patch.object(IPRoute, 'update_default')
    def test__put_default__delete_failed(self, mock_update_default):
        mock_update_default.side_effect = ValueError

        # case: failed to delete the default gateway
        message = Message({"data": {}, "query": {}, "param": {}})

        def resp(code=200, data=None):
            self.assertEqual(404, code)
        self.bundle._put_default(message=message, response=resp, test=True)

    @patch.object(IPRoute, "update_default")
    def test__put_default__add(self, mock_update_default):
        # case: add the default gateway
        message = Message({"data": {}, "query": {}, "param": {}})
        message.data["interface"] = "eth1"

        def resp(code=200, data=None):
            self.assertEqual(200, code)
        self.bundle._put_default(message=message, response=resp, test=True)

    """ TODO
    @patch.object(IPRoute, "update_default")
    def test_put_default_failed_recover_failed(self, mock_update_default):
        pass
    """

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

    @patch.object(IPRoute, "update_router")
    def test__event_router_db(self, mock_update_router):
        # case: update the router information by interface
        message = Message({"data": {}, "query": {}, "param": {}})
        message.data["interface"] = "eth1"
        message.data["gateway"] = "192.168.41.254"

        self.bundle._event_router_db(message=message, test=True)

    """
    @patch.object(IPRoute, "update_router")
    def test__hook_put_ethernet_by_id(self, mock_update_router):
        # case: test if default gateway changed
        message = Message({"data": {}, "query": {}, "param": {}})
        message.data["name"] = "eth1"

        def resp(code=200, data=None):
            self.assertEqual(200, code)
            self.assertEqual("eth0", data["interface"])
        self.bundle._hook_put_ethernet_by_id(message=message, response=resp,
                                             test=True)

    @patch.object(IPRoute, "update_router")
    def test__hook_put_ethernets(self, mock_update_router):
        # case: test if default gateway changed
        message = Message({"data": [], "query": {}, "param": {}})
        iface = {"id": 2, "name": "eth1", "gateway": "192.168.4.254"}
        message.data.append(iface)
        iface = {"id": 1, "name": "eth0", "gateway": "192.168.31.254"}
        message.data.append(iface)

        def resp(code=200, data=None):
            self.assertEqual(200, code)
            self.assertEqual("eth0", data["interface"])
        self.bundle._hook_put_ethernets(message=message, response=resp,
                                        test=True)
    """


if __name__ == "__main__":
    FORMAT = '%(asctime)s - %(levelname)s - %(lineno)s - %(message)s'
    logging.basicConfig(level=20, format=FORMAT)
    logger = logging.getLogger('IPRoute Test')
    unittest.main()
