#!/usr/bin/env python2.7
import platform
import unittest
import os
from os import unlink, stat
from random import random
from tempfile import mktemp
from threading import Thread

import imp
agent_file = os.path.dirname(os.path.abspath(__file__))+"/../agent/hibagent"
with open(agent_file) as fl:
    hibagent = imp.load_module('hibagent', fl, agent_file, ('py', 'rb', 1))

from time import sleep

try:
    from http.server import BaseHTTPRequestHandler, HTTPServer
except:
    import BaseHTTPServer
    BaseHTTPRequestHandler=BaseHTTPServer.BaseHTTPRequestHandler
    HTTPServer=BaseHTTPServer.HTTPServer

# Patch out a function that require actual root privileges
hibagent.update_kernel_swap_offset = lambda: 0

if platform.system() == "Darwin":
    os.O_DIRECT = 0  # Just pretend that it's there


class TestPmFreezeCurve(unittest.TestCase):
    def test_curve_parsing(self):
        curve = '0-8:20,8-16:40,16-64:60,64-128:150,128-256:200,256-:400'
        GB = 1024 ** 3
        self.assertEqual(20, hibagent.get_pm_freeze_timeout(curve, 7*GB))
        self.assertEqual(40, hibagent.get_pm_freeze_timeout(curve, 8*GB))
        self.assertEqual(200, hibagent.get_pm_freeze_timeout(curve, 128*GB))
        self.assertEqual(400, hibagent.get_pm_freeze_timeout(curve, 500*GB))

    def test_bad_curves(self):
        holey_curve = '0-8:20,16-64:60'
        GB = 1024**3
        self.assertIsNone(hibagent.get_pm_freeze_timeout(holey_curve, 9*GB))
        self.assertIsNone(hibagent.get_pm_freeze_timeout(holey_curve, 70*GB))
        self.assertEqual(20, hibagent.get_pm_freeze_timeout(holey_curve, 7*GB))
        self.assertEqual(60, hibagent.get_pm_freeze_timeout(holey_curve, 22*GB))


class TestHibernation(unittest.TestCase):
    def setUp(self):
        self.swapfile = mktemp()
        self.mkswap_flag = mktemp()
        self.swapon_flag = mktemp()

    def tearDown(self):
        def _unlink(fl):
            # noinspection PyBroadException
            try:
                unlink(fl)
            except:
                pass
        _unlink(self.swapfile)
        _unlink(self.mkswap_flag)
        _unlink(self.swapon_flag)

    def test_swap_initializer(self):
        si = hibagent.SwapInitializer(self.swapfile, 100663296,
                                      '/usr/bin/touch %s' % self.mkswap_flag,
                                      '/usr/bin/touch %s' % self.swapon_flag)
        # Default filler
        expected = b'b' * 1024
        self.do_fill_file(si, expected)

    def test_need_to_hurry(self):
        si = hibagent.SwapInitializer(self.swapfile, 100663296,
                                      '/usr/bin/touch %s' % self.mkswap_flag,
                                      '/usr/bin/touch %s' % self.swapon_flag)
        si.need_to_hurry = True
        # The file must be zero-padded
        expected = b'\0' * 1024
        self.do_fill_file(si, expected)

    def do_fill_file(self, si, expected_filler):

        si.init_swap()
        # Assert that the swapfile exists and is appropriately sized
        self.assertEqual(100663296, stat(self.swapfile).st_size)
        si.turn_on_swap()

        # Assert that we have 'turned on' the swap
        stat(self.swapon_flag)
        stat(self.mkswap_flag)

        with open(self.swapfile) as fl:
            while True:
                buf = os.read(fl.fileno(), 1024)
                if not buf:
                    break
                self.assertEqual(expected_filler, buf)


class FakeSwapper(object):
    def __init__(self):
        self.need_to_hurry = False
        self.finished = False
        self.turned_on = False

    def init_swap(self):
        while not self.finished and not self.need_to_hurry:
            sleep(0.1)

    def turn_on_swap(self):
        self.turned_on = True


class TestSwapInitializer(unittest.TestCase):
    def test_background_run(self):
        fs = FakeSwapper()
        bi = hibagent.BackgroundInitializerRunner(fs)
        bi.start_init()
        self.assertFalse(bi.check_finished())

        # Signal for the init end and check it
        fs.finished = True
        while not bi.check_finished():
            sleep(0.1)
        self.assertFalse(fs.need_to_hurry)
        self.assertTrue(fs.turned_on)

    def test_early_interrupt(self):
        fs = FakeSwapper()
        bi = hibagent.BackgroundInitializerRunner(fs)
        bi.start_init()
        self.assertFalse(bi.check_finished())
        bi.force_completion()
        self.assertTrue(fs.need_to_hurry)
        self.assertTrue(fs.turned_on)

    def test_error(self):
        def raiser():
            raise Exception("test")

        fs = FakeSwapper()
        bi = hibagent.BackgroundInitializerRunner(fs)
        fs.init_swap = raiser
        bi.start_init()
        try:
            while not bi.check_finished():
                sleep(0.1)
            self.fail("Should have thrown")
        except Exception as ex:
            self.assertEqual("test", str(ex))


global_content = ''


class SimpleHandler(BaseHTTPRequestHandler):
    def _set_headers(self, code):
        self.send_response(code)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        global global_content
        if global_content:
            self.send_error(200, global_content)
        else:
            self.send_error(404)


class ServerRunner(object):
    def __init__(self):
        self.port = int(random()*30000+10000)
        server_address = ('localhost', self.port)
        self.httpd = HTTPServer(server_address, SimpleHandler)

    def run(self):
        thread = Thread(target=self.httpd.serve_forever, name="SwapInitializer")
        thread.setDaemon(True)
        thread.start()

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()


class FakeInitializer(object):
    def __init__(self):
        self.forced = False
        self.finished = False

    def check_finished(self):
        return self.finished

    def force_completion(self):
        self.forced = True


class ItnPollerTest(unittest.TestCase):
    def setUp(self):
        self.server = ServerRunner()
        self.server.run()
        self.flagfile = mktemp()

    def tearDown(self):
        self.server.stop()
        # noinspection PyBroadException
        try:
            unlink(self.flagfile)
        except:
            pass

    def test_itn_polls(self):
        fi = FakeInitializer()
        poller = hibagent.ItnPoller("http://localhost:%d/blah" % self.server.port,
                                    '/usr/bin/touch %s' % self.flagfile, fi)
        poller.run_loop_iteration()
        # Nothing happens
        self.check_not_exists()

        # Signal the hibernation
        global global_content
        global_content = 'hibernate'

        poller.run_loop_iteration()
        # Now we should have hibernated
        self.assertTrue(fi.forced)
        stat(self.flagfile)

    def check_not_exists(self):
        # noinspection PyBroadException
        try:
            stat(self.flagfile)
            self.fail("Should not exist")
        except:
            pass


if __name__ == '__main__':
    unittest.main()
