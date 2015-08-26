#!/usr/bin/env python
# coding: utf-8

"""
Run this module by ``python -m slackbot.app``
"""

from tornado.ioloop import IOLoop
from tornado.web import Application
from tornado.httpserver import HTTPServer
from tornado.log import enable_pretty_logging

from .web import handlers
from .wsbot import start_wsbot
from . import settings


def main():
    enable_pretty_logging()

    io_loop = IOLoop.instance()

    # Web interface
    application = Application(handlers, debug=settings.DEBUG)
    for host, rules in application.handlers:
        for i in rules:
            print i.regex.pattern

    http_server = HTTPServer(application)
    http_server.listen(settings.PORT)

    # Websocket interface
    io_loop.add_callback(start_wsbot)

    print 'Starting ioloop ..'
    io_loop.start()


if __name__ == "__main__":
    main()
