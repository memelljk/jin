#!/usr/bin/env python
# coding: utf-8

from tornado.web import RequestHandler
from .core import client


class MainHandler(RequestHandler):
    def get(self):
        print self.request.arguments
        self.write("Hello, world")

    def post(self):
        self.write(self.request.arguments)


handlers = [
    (r'/send_message', MainHandler),
]
