#!/usr/bin/env python
# coding: utf-8


SLACK_TOKEN = NotImplemented

PORT = 9000


try:
    from .local_settings import *  # NOQA
except Exception as e:
    print 'Import local_settings error: %s' % e
