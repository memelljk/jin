#!/usr/bin/env python
# coding: utf-8

from slackclient import SlackClient
from . import settings


client = SlackClient(settings.SLACK_TOKEN)
