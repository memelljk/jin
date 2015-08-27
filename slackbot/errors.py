#!/usr/bin/env python
# coding: utf-8


class SlackbotBaseError(Exception):
    pass


class APICallFailed(SlackbotBaseError):
    """Failed to call Slack API"""
