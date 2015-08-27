#!/usr/bin/env python
# coding: utf-8

import json
import inspect
import logging
from tornado import gen
from tornado.websocket import websocket_connect
from tornado.log import enable_pretty_logging

from .core import APIClient
from .web import make_application
from .server import run_server
from .utils import ObjectDict, decorator_factory


class SlackBot(object):
    default_config = {
        'PORT': 9000,
        'DEBUG': True,
        'SLACK_TOKEN': NotImplemented,
    }
    required_config_keys = ['SLACK_TOKEN']

    def __init__(self, config_object):
        """Initalize bot with config"""
        self.apply_config_object(config_object)

        self.configure_logging()

        self.client = APIClient(self.config.SLACK_TOKEN)

        self.conn_pool = [None]
        self._web_handlers = []
        self._message_handlers = []

    @property
    def channels(self):
        if not hasattr(self, '_channels'):
            self._channels = self.client.get_channels()
        return self._channels

    def apply_config_object(self, config_object):
        config = ObjectDict(self.default_config)

        if inspect.ismodule(config_object):
            def has_k(k):
                return hasattr(config_object, k)

            def get_v(k):
                return getattr(config_object, k)
        elif isinstance(config_object, dict):
            def has_k(k):
                return k in config_object

            def get_v(k):
                return config_object[k]
        else:
            raise TypeError('config_object should be either a module or a dict')

        for k in self.default_config:
            if has_k(k):
                print 'Apply config %s' % k
                config[k] = get_v(k)

        for k in self.required_config_keys:
            if k not in config:
                raise KeyError('%s is required in config' % k)

        self.config = config

    def configure_logging(self):
        enable_pretty_logging()

        self.root_logger = logging.getLogger('')

        if self.config.DEBUG:
            self.root_logger.setLevel(logging.DEBUG)

    def route(self, url_regex):
        """Decorator to register a web handler"""
        def before_wrapper(func):
            url_spec = (url_regex, func)
            self._web_handlers.append(url_spec)

        return decorator_factory(before_wrapper=before_wrapper)

    def match_text(self, text_regex):
        """Decorator to register a message handler when text matchs the regex"""
        def before_wrapper(func):
            text_spec = (text_regex, func)
            self._message_handlers.append(text_spec)

        return decorator_factory(before_wrapper=before_wrapper)

    def get_ws_url(self):
        # Get url
        resp = self.client.server.api_requester.do(self.client.server.token, "rtm.start?simple_latest=1&no_unreads=1")
        body = resp.read().decode('utf-8')
        data = json.loads(body)
        ws_url = data['url']
        logging.info('Got ws url: %s', ws_url)
        return ws_url

    def send_message(self, text, channel_id=None, channel_name=None):
        if channel_id is None and channel_name is None:
            raise TypeError('Either channel_id or channel_name should be passed')

        if channel_name:
            channel_id = self._get_channel_id(channel_name)

        return self.client.send_message(channel_id, text)

    def _get_channel_id(self, name):
        for c in self.channels.itervalues():
            if c['name'] == name:
                return c['id']
        raise ValueError('No channel named %s' % name)

    @gen.coroutine
    def get_conn(self):
        if self.conn_pool[0] is None:
            ws_url = self.get_ws_url()
            # Assume this operation always success
            conn = yield websocket_connect(ws_url)
            self.conn_pool[0] = conn

        raise gen.Return(self.conn_pool[0])

    @gen.coroutine
    def start(self):
        """Start receiving message and handling
        """
        print 'Start recv from ws connection'
        conn = yield self.get_conn()

        while True:
            msg = yield conn.read_message()
            logging.info('Get msg: %s', msg)

    def run(self):
        """Run bot as a http server
        """
        application = make_application(self._web_handlers, {
            # If True, will make the server restart when file changes
            'debug': self.config.DEBUG,
        })

        run_server(self.start, application, self.config.PORT)
