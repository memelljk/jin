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
from .utils import ObjectDict, SearchList, decorator_factory


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

        # For `prepare`
        self.ws_url = None

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


    def _get_channel_id(self, name):
        for c in self.channels.itervalues():
            if c['name'] == name:
                return c['id']
        raise ValueError('No channel named %s' % name)

    @gen.coroutine
    def get_conn(self):
        if self.conn_pool[0] is None:
            # Assume this operation always success
            conn = yield websocket_connect(self.ws_url)
            self.conn_pool[0] = conn

        raise gen.Return(self.conn_pool[0])

    def prepare(self):
        # https://api.slack.com/methods/rtm.start
        rv = self.client.api_call('rtm.start?simple_latest=1&no_unreads=1')

        # TODO store users, channels here
        self.ws_url = rv['url']
        logging.info('Got ws url: %s', self.ws_url)

        self.selfinfo = ObjectDict(rv['self'])
        logging.info('Got selfinfo: %s', str(self.selfinfo)[:20])
        self.users = SearchList(rv['users'], ['id', 'name'])
        logging.info('Got users: %s', str(self.users)[:20])
        self.channels = SearchList(rv['channels'], ['id', 'name'])
        logging.info('Got channels: %s', str(self.channels)[:20])
        self.groups = SearchList(rv['groups'], ['id', 'name'])
        logging.info('Got groups: %s', str(self.groups)[:20])

    @gen.coroutine
    def start(self):
        """Start receiving message and handling
        """
        self.prepare()
        conn = yield self.get_conn()

        logging.info('Start recv from ws connection')
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
