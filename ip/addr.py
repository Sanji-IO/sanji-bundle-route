#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import sh
import netifaces
import ipcalc
import logging

# https://www.kernel.org/doc/Documentation/ABI/testing/sysfs-class-net

# Used python modules:
# setuptools
#   https://pypi.python.org/pypi/setuptools
#
# ipcalc.py
#   https://github.com/tehmaze/ipcalc/
#
# sh.py
#   https://pypi.python.org/pypi/sh


_logger = logging.getLogger("sanji.ethernet.ip.addr")


def interfaces():
    """List all interfaces.

    Returns:
        A list of interface names. For example:

        ["eth0", "eth1", "wlan0"]

    Raises:
        FIXME
    """
    # ifaces=$(ip a show | grep -Eo "[0-9]: wlan[0-9]" | sed "s/.*wlan//g")
    # ifaces=$(ip a show | grep -Eo '[0-9]: eth[0-9]' | awk '{print $2}')
    try:
        ifaces = netifaces.interfaces()
        ifaces = [x for x in ifaces if not
                  (x.startswith("lo") or x.startswith("mon."))]
        return ifaces
    except Exception, e:
        _logger.info("Cannot get interfaces: %s" % e)
        raise e


def ifaddresses(iface):
    """Retrieve the detail information for an interface.

    Args:
        iface: interface name.

    Returns:
        A dict format data will be return. For example:

        {"mac": "",
         "link": 1,
         "inet": [{
             "ip": "",
             "netmask": "",
             "subnet": "",
             "broadcast": ""}]}

    Raises:
        ValueError: You must specify a valid interface name.
    """
    full = netifaces.ifaddresses(iface)

    info = {}
    info["mac"] = full[netifaces.AF_LINK][0]['addr']

    try:
        info["link"] = open("/sys/class/net/%s/operstate" % iface).read()
        if "down" == info["link"][:-1]:
            info["link"] = 0
        else:
            info["link"] = open("/sys/class/net/%s/carrier" % iface).read()
            info["link"] = int(info["link"][:-1])  # convert to int
    except:
        info["link"] = 0

    info["inet"] = []
    for ip in full[netifaces.AF_INET]:
        item = {}
        item["ip"] = ip['addr']
        item["netmask"] = ip['netmask']
        item["broadcast"] = ip["broadcast"]
        net = ipcalc.Network("%s/%s" % (ip['addr'], ip['netmask']))
        item["subnet"] = str(net.network())
        info["inet"].append(item)

    return info


def ifupdown(iface, up):
    """Set an interface to up or down status.

    Args:
        iface: interface name.
        up: status for the interface, True for up and False for down.

    Raises:
        ValueError
    """
    if not up:
        try:
            output = sh.awk(
                sh.grep(sh.grep(sh.ps("ax"), iface), "dhclient"),
                "{print $1}")
            dhclients = output().split()
            for dhclient in dhclients:
                sh.kill(dhclient)
        except:
            pass
    try:
        sh.ip("link", "set", iface, "up" if up else "down")
    except:
        raise ValueError("Cannot update the link status for \"%s\"."
                         % iface)


def ifconfig(iface, dhcpc, ip="", netmask="24", gateway="", script=None):
    """Set the interface to static IP or dynamic IP (by dhcpclient).

    Args:
        iface: interface name.
        dhcpc: True for using dynamic IP and False for static.
        ip: IP address for static IP
        netmask:
        gateway:

    Raises:
        ValueError
    """
    # TODO(aeluin) catch the exception?
    # Check if interface exist
    try:
        sh.ip("addr", "show", iface)
    except sh.ErrorReturnCode_1:
        raise ValueError("Device \"%s\" does not exist." % iface)
    except:
        raise ValueError("Unknown error for \"%s\"." % iface)

    # Disable the dhcp client and flush interface
    try:
        dhclients = sh.awk(
            sh.grep(sh.grep(sh.ps("ax"), iface), "dhclient"),
            "{print $1}")
        dhclients = dhclients.split()
        if 1 == len(dhclients):
            sh.dhclient("-x", iface)
        elif len(dhclients) > 1:
            for dhclient in dhclients:
                sh.kill(dhclient)
    except:
        pass

    try:
        sh.ip("-4", "addr", "flush", "label", iface)
    except:
        raise ValueError("Unknown error for \"%s\"." % iface)

    if dhcpc:
        if script:
            sh.dhclient("-sf", script, iface)
        else:
            sh.dhclient(iface)
    else:
        if ip:
            net = ipcalc.Network("%s/%s" % (ip, netmask))
            sh.ip("addr", "add", "%s/%s" % (ip, net.netmask()), "broadcast",
                  net.broadcast(), "dev", iface)


if __name__ == "__main__":
    print interfaces()

    # ifconfig("eth0", True)
    # time.sleep(10)
    # ifconfig("eth1", False, "192.168.31.36")
    eth0 = ifaddresses("eth0")
    print eth0
    print "link: %d" % eth0["link"]
    for ip in eth0["inet"]:
        print "ip: %s" % ip["ip"]
        print "netmask: %s" % ip["netmask"]
        if "subnet" in ip:
            print "subnet: %s" % ip["subnet"]

    '''
    ifupdown("eth1", True)
    # ifconfig("eth1", True)
    ifconfig("eth1", False, "192.168.31.39")

    eth1 = ifaddresses("eth1")
    print "link: %d" % eth1["link"]
    for ip in eth1["inet"]:
        print "ip: %s" % ip["ip"]
        print "netmask: %s" % ip["netmask"]
        if "subnet" in ip:
            print "subnet: %s" % ip["subnet"]
    '''
