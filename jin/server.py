#!/usr/bin/env python
# coding: utf-8

from tornado.ioloop import IOLoop
from tornado.httpserver import HTTPServer


def run_server(start_ws, application, port):

    io_loop = IOLoop.instance()

    # Websocket interface
    io_loop.add_callback(start_ws)

    # Web interface
    http_server = HTTPServer(application)
    http_server.listen(port)

    print 'Starting ioloop ..'
    io_loop.start()
