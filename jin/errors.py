#!/usr/bin/env python
# coding: utf-8


class JinBaseError(Exception):
    pass


class APICallFailed(JinBaseError):
    """Failed to call Slack API"""


class ReplyFailed(JinBaseError):
    """Failed to generate/send a reply"""
