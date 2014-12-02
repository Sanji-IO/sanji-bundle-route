#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import logging
from time import sleep

from sanji.core import Sanji
from sanji.connection.mqtt import Mqtt


REQ_RESOURCE = '/network/routes'
MANUAL_TEST = 0


class View(Sanji):

    # This function will be executed after registered.
    def run(self):

        for count in xrange(0, 100, 1):
            # Normal CRUD Operation
            #   self.publish.[get, put, delete, post](...)
            # One-to-One Messaging
            #   self.publish.direct.[get, put, delete, post](...)
            #   (if block=True return Message, else return mqtt mid number)
            # Agruments
            #   (resource[, data=None, block=True, timeout=60])

            # case 1: test GET available interfaces
            resource = '%s/interfaces' % REQ_RESOURCE
            print 'GET %s' % resource
            res = self.publish.get(resource)
            if res.code != 200:
                print 'GET should be supported, code 200 is expected'
                print res.to_json()
                self.stop()
            if 1 == MANUAL_TEST:
                var = raw_input("Please enter any key to continue...")

            # case 2: test GET current default gateway setting
            sleep(2)
            resource = '%s/default' % REQ_RESOURCE
            print 'GET %s' % resource
            res = self.publish.get(resource)
            if res.code != 200:
                print 'GET should be supported, code 200 is expected'
                print res.to_json()
                self.stop()
            if 1 == MANUAL_TEST:
                var = raw_input("Please enter any key to continue...")

            # case 3: test PUT with no data (remove default gateway)
            sleep(2)
            resource = '%s/default' % REQ_RESOURCE
            print 'PUT %s' % resource
            res = self.publish.put(resource, None)
            if res.code != 400:
                print 'data is required, code 400 is expected'
                print res.to_json()
                self.stop()
            if 1 == MANUAL_TEST:
                var = raw_input("Please enter any key to continue...")

            # case 4: test PUT with empty data (remove default gateway)
            sleep(2)
            resource = '%s/default' % REQ_RESOURCE
            print 'PUT %s' % resource
            res = self.publish.put(resource, data={})
            if res.code != 200:
                print 'data is not required, code 200 is expected'
                print res.to_json()
                self.stop()
            if 1 == MANUAL_TEST:
                var = raw_input("Please enter any key to continue...")

            # case 5: test PUT to update default gateway
            sleep(2)
            resource = '%s/default' % REQ_RESOURCE
            print 'PUT %s' % resource
            res = self.publish.put(resource, data={"interface": "eth0"})
            if res.code != 200:
                print 'PUT with interface is supported, code 200 is expected'
                print res.to_json()
                self.stop()
            if 1 == MANUAL_TEST:
                var = raw_input("Please enter any key to continue...")

            # case 6: test PUT to update default gateway
            sleep(2)
            resource = '%s/default' % REQ_RESOURCE
            print 'PUT %s' % resource
            res = self.publish.put(
                resource,
                data={"interface": "eth0", "gateway": "192.168.31.254"})
            if res.code != 200:
                print 'PUT with interface is supported, code 200 is expected'
                print res.to_json()
                self.stop()
            if 1 == MANUAL_TEST:
                print var

            # stop the test view
            self.stop()


if __name__ == '__main__':
    FORMAT = '%(asctime)s - %(levelname)s - %(lineno)s - %(message)s'
    logging.basicConfig(level=0, format=FORMAT)
    logger = logging.getLogger('IPRoute')

    view = View(connection=Mqtt())
    view.start()
