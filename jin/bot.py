#!/usr/bin/env python
# coding: utf-8

import json
import inspect
import logging
import traceback
from tornado import gen
from tornado.websocket import websocket_connect
from tornado.log import enable_pretty_logging
from tornado.ioloop import PeriodicCallback

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

        self.register_default_events()
        self.register_periodic_callback()

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
        """
        ``event_type`` could be a string or tuple
        """
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

    def register_default_events(self):
        """Register some default event handlers to grant the bot basic
        functionality & intelligence, e.g. update channels upon
        channel_created & other events.
        """
        # TODO add some default events to:
        # 1. Keep channels, groups, users up to date
        # 2. Default reply for direct message if not implement

    def register_periodic_callback(self, second=60):
        PeriodicCallback(
            self._check_connection, second * 1000).start()

    def _check_connection(self):
        conn = self.conn_pool[0]
        if conn:
            if conn.protocol:
                conn.protocol.write_ping(b'a')
                logging.debug('Ping: a')
            return

            logging.debug(
                'Connection: .protocol.*_terminated %s %s; .stream.close() %s; .tcp_client.resolver.executor %s',
                conn.protocol.client_terminated,
                conn.protocol.server_terminated,
                conn.stream.closed(),
                conn.tcp_client.resolver.executor,
            )
        else:
            logging.warn('No connection in conn_pool')

    @gen.coroutine
    def get_conn(self):
        if self.conn_pool[0] is None:
            # Assume this operation always success
            conn = yield websocket_connect(self.ws_url)
            self.conn_pool[0] = conn

            print 'conn', conn, dir(conn)
            print conn.__dict__

        raise gen.Return(self.conn_pool[0])

    def recycle_conn(self):
        """Close current connection and clear conn_pool
        """
        logging.info('Recycle old connection %s', self.conn_pool)
        conn = self.conn_pool[0]
        if conn is not None:
            conn.close()

        self.conn_pool[0] = None

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
        """Start the bot service, keep underlying `_start` in a while True loop
        """
        while True:
            try:
                yield self._start()
            except errors.WSConnectionClosed as e:
                logging.warn('Connection was closed: %s', e)
                self.recycle_conn()

    @gen.coroutine
    def _start(self):
        """Establish websocket connection and start receiving and handling messages
        """
        self.prepare()
        conn = yield self.get_conn()

        logging.info('Start recv from ws connection')
        while True:
            logging.debug('!Read message')

            msg_str = yield conn.read_message()

            logging.debug('!Got msg str, %s', msg_str)

            # Since when connection is closed, `read_message` got `None`,
            # there's no need to override `WebSocketClientConnection.on_close`,
            # just do reconnect if `msg_str` is `None`.
            if msg_str is None:
                raise errors.WSConnectionClosed(
                    'Got None from read_message, means connection is closed')

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
            msg_subtype = msg.subtype
            #logging.debug('msg type %s %s', msg_type, event_type)

            if match_event_type((msg_type, msg_subtype), event_type):
                logging.info('Match event_type %s, call handler %s', event_type, handler_func)
                # TODO more options
                #match_key=match_key,
                #match_pattern=match_pattern,
                #break_loop=break_loop,

                output = handler_func(msg)
                if output is None:
                    logging.debug('output is None, skip')
                else:
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

    def send_message(self, *args, **kwargs):
        """Simple """

    def run(self):
        """Run bot as a http server
        """
        application = make_application(self._web_handlers, {
            # If True, will make the server restart when file changes
            'debug': self.config.DEBUG,
        })

        run_server(self.start, application, self.config.PORT)


def match_event_type(types, event_type):
    if isinstance(event_type, basestring):
        return types[0] == event_type
    else:  # tuple
        return types == event_type
