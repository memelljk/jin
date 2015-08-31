#!/usr/bin/env python
# coding: utf-8

# TODO remove slackclient, just use the original HTTP API

import json
import logging
import traceback
from slackclient import SlackClient
from .errors import APICallFailed


class APIClient(object):
    def __init__(self, token):
        self.token = token
        self.client = SlackClient(token)

    def api_call(self, *args, **kwargs):
        try:
            rv = self.client.api_call(*args, **kwargs)
            return json.loads(rv)
        except Exception as e:
            traceback.print_exc()
            raise APICallFailed(str(e))

    def get_channels(self):
        channels = {}
        channel_names = []
        keep_keys = ['id', 'name', 'is_archived', 'is_member']
        logging.info('call api channels.list')
        rv = self.api_call('channels.list')
        for i in rv['channels']:
            c = {k: v for k, v in i.iteritems() if k in keep_keys}
            channels[c['id']] = c
            channel_names.append(c['name'])
        logging.debug('Got channels: %s', ','.join(channel_names))
        return channels

    def send_message(self, channel_id, text, as_user=True, **kwargs):
        """
        Reference: https://api.slack.com/methods/chat.postMessage
        """

        api_args = dict(channel=channel_id, text=text)
        if as_user:
            api_args['as_user'] = 'true'
        api_args.update(kwargs)
        logging.info('call api chat.postMessage: %s', api_args)

        rv = self.api_call('chat.postMessage', **api_args)
        logging.debug('postMessage finished: %s', rv)
        return rv
