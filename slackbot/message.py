#!/usr/bin/env python
# coding: utf-8

from . import errors


class Message(object):
    """Message is the request user send to slack, read from RTM API"""

    def __init__(self, raw, bot):
        self.raw = raw
        self.bot = bot

    @property
    def user(self):
        return self.raw.get('user')

    @property
    def type(self):
        return self.raw.get('type')

    def get_channel_id(self):
        return self.raw.get('channel')

    def reply(self, text, channel=None, channel_id=None, **kwargs):

        # Using message's channel
        if not channel and not channel_id:
            channel_id = self.get_channel_id()
            if not channel_id:
                raise errors.ReplyFailed(
                    'Neither a channel is specified, nor the message has a channel: %s', self.raw)
        else:
            if not channel_id and channel:
                channel_item = self.bot.channels.get(name=channel)
                if not channel_item:
                    raise errors.ReplyFailed('Channel %s not found', channel)
                channel_id = channel_item['id']

        # Ensure channel_id is not None
        if not channel_id:
            raise errors.ReplyFailed('WTF! %s, %s' % (channel, channel_id))

        return Reply(channel_id, text, **kwargs)

    # TODO
    def reply_to_user(self):
        pass

    def __str__(self):
        return '<Message: {}>'.format(self.raw)


class Reply(object):
    """Reply is what reply to slack by the robot"""

    def __init__(self, channel_id, text, **kwargs):
        self.channel_id = channel_id
        self.text = text
        self.extra_args = kwargs

    def __str__(self):
        return '<Reply: [{}] {}, {}>'.format(self.channel_id, self.text, self.extra_args)
