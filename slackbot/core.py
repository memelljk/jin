#!/usr/bin/env python
# coding: utf-8

import json
from slackclient import SlackClient
from . import settings


client = SlackClient(settings.SLACK_TOKEN)


def get_channels():
    channels = {}
    keep_keys = ['id', 'name', 'is_archived', 'is_member']
    rv = json.loads(client.api_call('channels.list'))
    for i in rv['channels']:
        c = {k: v for k, v in i.iteritems() if k in keep_keys}
        channels[c['id']] = c
    return channels
