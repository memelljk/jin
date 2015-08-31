#!/usr/bin/env python
# coding: utf-8

import json
import inspect
import logging
import traceback
from tornado import gen
from tornado.websocket import websocket_connect
from tornado.log import enable_pretty_logging

from .core import APIClient
from .web import make_application
from .server import run_server
from .utils import ObjectDict, SearchList, decorator_factory
from .message import Message, Reply
from . import errors


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
            logging.debug('Enable DEBUG logging')

    def route(self, url_pattern):
        """Decorator to register a web handler"""
        def before_wrapper(func):
            spec = (url_pattern, func)
            self._web_handlers.append(spec)

        return decorator_factory(before_wrapper=before_wrapper)

    def on_event(self, event_type, match_key=None, match_pattern=None, break_loop=False):
        def before_wrapper(func):
            options = dict(
                match_key=match_key,
                match_pattern=match_pattern,
                break_loop=break_loop,
            )
            spec = (event_type, func, options)
            self._message_handlers.append(spec)

        return decorator_factory(before_wrapper=before_wrapper)

    def match_text(self, text_regex, break_loop=False):
        """Decorator to register a message handler when text matchs the regex"""
        #compiled = re.compile(text_regex)
        pass

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
            msg_str = yield conn.read_message()
            try:
                msg = Message(json.loads(msg_str), self)
            except Exception as e:
                logging.error('Parse message failed: %s; msg: %s', e, msg_str)
                continue
            else:
                try:
                    yield self.handle_message(msg)
                except Exception as e:
                    logging.error('Handle message failed, %s\n%s', e, traceback.format_exc())

    @gen.coroutine
    def handle_message(self, msg):
        logging.info('Got msg: %s', msg)
        #logging.debug('msg handlers %s', self._message_handlers)

        # Ignore bot itself
        if msg.user and msg.user == self.selfinfo['id']:
            logging.debug('Got message from bot itself, ignore: %s', msg)
            return

        for event_type, handler_func, options in self._message_handlers:
            msg_type = msg.type
            #logging.debug('msg type %s %s', msg_type, event_type)
            if msg_type == event_type:
                logging.info('Event type %s, call handler %s', event_type, handler_func)
                # TODO more options
                #match_key=match_key,
                #match_pattern=match_pattern,
                #break_loop=break_loop,

                output = handler_func(msg)
                self.handle_output(output, msg)

                if options.get('break_loop'):
                    logging.info('Break message handling loop')
                    break

    def handle_output(self, output, msg):
        # text:
        # {u'text': u'a', u'ts': u'1440669389.000032', u'user': u'U03URT0PU', u'team': u'T02Q87WRQ', u'type': u'message', u'channel': u'C09J98JLV'}

        # The canonical way to reply
        if isinstance(output, Reply):
            pass
        # TODO the simple way
        # elif isinstance(output, basestring)
        else:
            raise errors.ReplyFailed(
                'Could not handle output: %s, %s' % (type(output), output))

        # Ensure output is a Reply object
        self.send_reply(output)

    def send_reply(self, reply):
        logging.info('Send reply: %s', reply)
        return self.client.send_message(reply.channel_id, reply.text, **reply.extra_args)

    def run(self):
        """Run bot as a http server
        """
        application = make_application(self._web_handlers, {
            # If True, will make the server restart when file changes
            'debug': self.config.DEBUG,
        })

        run_server(self.start, application, self.config.PORT)
