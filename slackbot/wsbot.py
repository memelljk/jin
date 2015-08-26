#!/usr/bin/env python
# coding: utf-8

"""
Websocket bot
"""

import json
import logging
from tornado import gen
from tornado.websocket import websocket_connect
from .core import client


ws_conn_pool = [None]


def get_ws_url():
    # Get url
    resp = client.server.api_requester.do(client.server.token, "rtm.start?simple_latest=1&no_unreads=1")
    body = resp.read().decode('utf-8')
    data = json.loads(body)
    ws_url = data['url']
    logging.info('Got ws url: %s', ws_url)
    return ws_url


@gen.coroutine
def get_ws_conn():
    if ws_conn_pool[0] is None:
        ws_url = get_ws_url()
        # Assume this operation always success
        conn = yield websocket_connect(ws_url)
        ws_conn_pool[0] = conn

    raise gen.Return(ws_conn_pool[0])


@gen.coroutine
def start_wsbot(*args, **kwargs):
    print 'call start_ws'

    conn = yield get_ws_conn()

    while True:
        msg = yield conn.read_message()
        logging.info('Get msg: %s', msg)
