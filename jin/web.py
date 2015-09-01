#!/usr/bin/env python
# coding: utf-8

from tornado.web import Application, RequestHandler


def make_application(handlers, options):
    """Make a simple tornado application"""

    application = Application(handlers, **options)
    for host, rules in application.handlers:
        for i in rules:
            print i.regex.pattern

    return application


class SlackHandler(RequestHandler):
    pass


# TODO common control APIs (update info etc)
