#!/usr/bin/env python
# -*- coding: UTF-8 -*-


import os
import sys
import logging
import unittest

from mock import patch
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

    def setUp(self):
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
            os.remove("%s/data/%s.backup.json" % (dirpath, self.name))
        except OSError:
            pass

    def test_init_no_conf(self):
        # case: no configuration file
        with self.assertRaises(IOError):
            with patch("route.ModelInitiator") as mock_modelinit:
                mock_modelinit.side_effect = IOError
                self.bundle.init()

    def test_load_current_conf(self):
        # case: load current configuration
        self.bundle.load(dirpath)
        self.assertEqual("eth0", self.bundle.model.db["interface"])

    def test_load_backup_conf(self):
        # case: load backup configuration
        os.remove("%s/data/%s.json" % (dirpath, self.name))
        self.bundle.load(dirpath)
        self.assertEqual("eth0", self.bundle.model.db["interface"])

    def test_load_no_conf(self):
        # case: cannot load any configuration
        with self.assertRaises(IOError):
            self.bundle.load("%s/mock" % dirpath)

    def test_save(self):
        # Already tested in init()
        pass

    @patch.object(IPRoute, 'update_default')
    def test_cellular_connected_up(self, mock_update_default):
        # case: update default gateway when cellular connected
        self.bundle.cellular_connected("ppp0")
        self.assertEqual("ppp0", self.bundle.cellular)

    @patch.object(IPRoute, 'update_default')
    def test_cellular_connected_down(self, mock_update_default):
        # case: update default gateway when cellular disconnected
        self.bundle.cellular_connected("ppp0", False)
        self.assertEqual(None, self.bundle.cellular)

    @patch.object(IPRoute, 'update_default')
    def test_cellular_connected_down_delete(self, mock_update_default):
        # case: update default gateway when cellular disconnected
        self.bundle.model.db["interface"] = "ppp0"
        self.bundle.cellular_connected("ppp0", False)
        self.assertEqual(None, self.bundle.cellular)

    @patch("route.ip.addr.ifaddresses")
    @patch("route.ip.addr.interfaces")
    def test_list_interfaces(self, mock_interfaces, mock_ifaddresses):
        # case: list the available interfaces
        mock_interfaces.return_value = ["eth0", "eth1", "ppp0"]
        mock_ifaddresses.side_effect = mock_ip_addr_ifaddresses

        ifaces = self.bundle.list_interfaces()
        self.assertEqual(2, len(ifaces))
        self.assertIn("eth0", ifaces)
        self.assertIn("ppp0", ifaces)

    @patch("route.ip.addr.interfaces")
    def test_list_interfaces_failed_get_ifaces(self, mock_interfaces):
        # case: failed to list the available interfaces
        mock_interfaces.side_effect = IOError

        ifaces = self.bundle.list_interfaces()
        self.assertEqual(None, ifaces)

    @patch("route.ip.addr.ifaddresses")
    @patch("route.ip.addr.interfaces")
    def test_list_interfaces_failed_get_status(self, mock_interfaces,
                                               mock_ifaddresses):
        # case: cannot get some interface's status
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

    @patch("route.ip.route.delete")
    def test_update_default_delete(self, mock_route_delete):
        # case: delete the default gateway
        default = dict()
        self.bundle.update_default(default)
        self.assertNotIn("interface", self.bundle.model.db)

    @patch("route.ip.route.delete")
    def test_update_default_delete_failed(self, mock_route_delete):
        mock_route_delete.side_effect = IOError

        # case: failed to delete the default gateway
        default = dict()
        with self.assertRaises(IOError):
            self.bundle.update_default(default)
        self.assertIn("interface", self.bundle.model.db)

    @patch("route.ip.route.add")
    @patch("route.ip.route.delete")
    @patch.object(IPRoute, 'list_interfaces')
    def test_update_default_add_without_gateway(
            self, mock_list_interfaces, mock_route_delete, mock_route_add):
        mock_list_interfaces.return_value = ["eth0", "eth1"]

        # case: add the default gateway
        default = dict()
        default["interface"] = "eth1"
        self.bundle.update_default(default)
        self.assertIn("eth1", self.bundle.model.db["interface"])

    @patch("route.ip.route.add")
    @patch("route.ip.route.delete")
    @patch.object(IPRoute, 'list_interfaces')
    def test_update_default_add_with_gateway(
            self, mock_list_interfaces, mock_route_delete, mock_route_add):
        mock_list_interfaces.return_value = ["eth0", "eth1"]

        # case: add the default gateway
        default = dict()
        default["interface"] = "eth1"
        default["gateway"] = "192.168.4.254"
        self.bundle.update_default(default)
        self.assertIn("eth1", self.bundle.model.db["interface"])

    @patch.object(IPRoute, 'list_interfaces')
    def test_update_default_add_failed_iface_down(self, mock_list_interfaces):
        mock_list_interfaces.return_value = ["eth0"]

        # case: fail to add the default gateway when indicated interface is
        # down
        default = dict()
        default["interface"] = "eth1"
        default["gateway"] = "192.168.4.254"
        with self.assertRaises(ValueError):
            self.bundle.update_default(default)
        self.assertIn("interface", self.bundle.model.db)

    @patch.object(IPRoute, 'list_interfaces')
    def test_update_default_add_failed_cellular_connected(
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
    def test_update_default_add_failed(
            self, mock_list_interfaces, mock_route_delete, mock_route_add):
        mock_list_interfaces.return_value = ["eth0", "eth1"]
        mock_route_add.side_effect = ValueError

        # case: fail to add the default gateway
        default = dict()
        default["interface"] = "eth0"
        default["gateway"] = "192.168.3.254"
        with self.assertRaises(ValueError):
            self.bundle.update_default(default)

    @patch("route.ip.addr.ifaddresses")
    @patch("route.ip.addr.interfaces")
    def test_get_interfaces(self, mock_interfaces, mock_ifaddresses):
        mock_interfaces.return_value = ["eth0", "eth1", "ppp0"]
        mock_ifaddresses.side_effect = mock_ip_addr_ifaddresses

        # case: get supported interface list
        message = Message({"data": {}, "query": {}, "param": {}})

        def resp(code=200, data=None):
            self.assertEqual(200, code)
            self.assertEqual(2, len(data))
            self.assertIn("eth0", data)
            self.assertIn("ppp0", data)
        self.bundle.get_interfaces(message=message, response=resp, test=True)

    @patch("route.ip.addr.interfaces")
    def test_get_interfaces_failed(self, mock_interfaces):
        mock_interfaces.side_effect = ValueError

        # case: fail to get supported interface list
        message = Message({"data": {}, "query": {}, "param": {}})

        def resp(code=404, data=None):
            self.assertEqual(404, code)
            self.assertEqual(None, data)
        self.bundle.get_interfaces(message=message, response=resp, test=True)

    def test_get_default(self):
        # case: get default gateway info.
        message = Message({"data": {}, "query": {}, "param": {}})

        def resp(code=200, data=None):
            self.assertEqual(200, code)
            self.assertEqual("eth0", data["interface"])
        self.bundle.get_default(message=message, response=resp, test=True)

    def test_get_default_empty(self):
        self.bundle.model.db = {}

        # case: no default gateway set
        message = Message({"data": {}, "query": {}, "param": {}})

        def resp(code=200, data=None):
            self.assertEqual(200, code)
            self.assertEqual({}, data)
        self.bundle.get_default(message=message, response=resp, test=True)

    def test_put_default_none(self):
        # case: None data is not allowed
        message = Message({"data": None, "query": {}, "param": {}})

        def resp(code=200, data=None):
            self.assertEqual(400, code)
        self.bundle.put_default(message=message, response=resp, test=True)

    @patch.object(IPRoute, 'update_default')
    def test_put_default_delete(self, mock_update_default):
        # case: delete the default gateway
        message = Message({"data": {}, "query": {}, "param": {}})

        def resp(code=200, data=None):
            self.assertEqual(200, code)
        self.bundle.put_default(message=message, response=resp, test=True)

    @patch.object(IPRoute, 'update_default')
    def test_put_default_delete_with_empty_iface(self, mock_update_default):
        # case: delete the default gateway
        message = Message(
            {"data": {"interface": ""}, "query": {}, "param": {}})

        def resp(code=200, data=None):
            self.assertEqual(200, code)
        self.bundle.put_default(message=message, response=resp, test=True)

    @patch.object(IPRoute, 'update_default')
    def test_put_default_delete_failed(self, mock_update_default):
        mock_update_default.side_effect = ValueError

        # case: failed to delete the default gateway
        message = Message({"data": {}, "query": {}, "param": {}})

        def resp(code=200, data=None):
            self.assertEqual(404, code)
        self.bundle.put_default(message=message, response=resp, test=True)

    @patch.object(IPRoute, "update_default")
    def test_put_default_add(self, mock_update_default):
        # case: add the default gateway
        message = Message({"data": {}, "query": {}, "param": {}})
        message.data["interface"] = "eth1"

        def resp(code=200, data=None):
            self.assertEqual(200, code)
        self.bundle.put_default(message=message, response=resp, test=True)

    """ TODO
    @patch.object(IPRoute, "update_default")
    def test_put_default_failed_recover_failed(self, mock_update_default):
        pass
    """

    def test_hook_put_ethernet_by_id_no_change(self):
        # case: test if default gateway changed
        message = Message({"data": {}, "query": {}, "param": {}})
        message.data["name"] = "eth1"

        def resp(code=200, data=None):
            self.assertEqual(200, code)
            self.assertEqual("eth0", data["interface"])
        self.bundle.hook_put_ethernet_by_id(message=message, response=resp,
                                            test=True)

    @patch.object(IPRoute, "update_default")
    def test_hook_put_ethernet_by_id(self, mock_update_default):
        # case: test if default gateway changed
        message = Message({"data": {}, "query": {}, "param": {}})
        message.data["name"] = "eth0"
        message.data["gateway"] = "192.168.31.254"

        def resp(code=200, data=None):
            self.assertEqual(200, code)
            self.assertEqual("eth0", data["interface"])
        self.bundle.hook_put_ethernet_by_id(message=message, response=resp,
                                            test=True)

    def test_hook_put_ethernets_no_change(self):
        # case: test if default gateway changed
        message = Message({"data": [], "query": {}, "param": {}})
        iface = {"id": 2, "name": "eth1", "gateway": "192.168.4.254"}
        message.data.append(iface)
        iface = {"id": 3, "name": "eth2", "gateway": "192.168.5.254"}
        message.data.append(iface)

        def resp(code=200, data=None):
            self.assertEqual(200, code)
            self.assertEqual("eth0", data["interface"])
        self.bundle.hook_put_ethernets(message=message, response=resp,
                                       test=True)

    @patch.object(IPRoute, "update_default")
    def test_hook_put_ethernets(self, mock_update_default):
        # case: test if default gateway changed
        message = Message({"data": [], "query": {}, "param": {}})
        iface = {"id": 2, "name": "eth1", "gateway": "192.168.4.254"}
        message.data.append(iface)
        iface = {"id": 1, "name": "eth0", "gateway": "192.168.31.254"}
        message.data.append(iface)

        def resp(code=200, data=None):
            self.assertEqual(200, code)
            self.assertEqual("eth0", data["interface"])
        self.bundle.hook_put_ethernets(message=message, response=resp,
                                       test=True)


if __name__ == "__main__":
    FORMAT = '%(asctime)s - %(levelname)s - %(lineno)s - %(message)s'
    logging.basicConfig(level=20, format=FORMAT)
    logger = logging.getLogger('IPRoute Test')
    unittest.main()
