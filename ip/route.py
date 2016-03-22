#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import sh


def show():
    """List all routing rules.

    Returns:
        A list of dict for each routing rule.

        [
            {"dest": "",
                "src": "",
                "dev": ""},
            {"default": "",
                "dev": ""}
        ]
    """
    rules = []
    routes = sh.ip("route", "show")
    for route in routes:
        rule = dict()
        route = route.split()
        if "default" == route[0]:
            rule["default"] = ""
            if "via" in route:
                rule["default"] = route[route.index("via")+1]
            rule["dev"] = route[route.index("dev")+1]
        else:
            rule["dest"] = route[0]
            rule["dev"] = route[route.index("dev")+1]
            if "src" in route:
                src = route.index("src")
            elif "via" in route:
                src = route.index("via")
            else:
                src = -1
            if -1 != src:
                rule["src"] = route[src+1]
        rules.append(rule)
    return rules


def add(dest, dev="", src=""):
    """Add a routing rule.

    Args:
        dest: destination for the routing rule, default for default route.
        dev: routing device, could be empty
        src: source for the routing rule, fill "gateway" if dest is "default"

    Raises:
        FIXME
    """
    if "" == src:
        sh.ip("route", "add", dest, "dev", dev)
    elif "default" == dest:
        if dev:
            sh.ip("route", "add", dest, "dev", dev, "via", src)
        else:
            sh.ip("route", "add", dest, "via", src)
    else:
        sh.ip("route", "add", dest, "dev", dev, "proto", "kernel", "scope",
              "link", "src", src)


def delete(network="default"):
    """Delete a routing rule.

    Args:
        network: destination of the routing rule to be delete

    Raises:
        FIXME
    """
    try:
        sh.ip("route", "del", network)
    except sh.ErrorReturnCode_2:
        pass


if __name__ == "__main__":
    print show()
