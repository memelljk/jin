#!/usr/bin/env python
# coding: utf-8

from jin import SlackBot
from jin.web import SlackHandler
import mybot_config


bot = SlackBot(mybot_config)


@bot.on_event('hello')
def hello(msg):
    return msg.reply("I'm online!", channel='slack-test')


@bot.on_event(('message', None))
def repeat(msg):
    # Only respond in #slack-test
    if msg.channel == 'slack-test':
        return msg.reply('You just said: %s' % msg.raw['text'])


@bot.route('/send')
class SendHandler(SlackHandler):
    def get(self):
        text = self.get_argument('text')
        channel = self.get_argument('channel')
        channel_id = bot.channels.get(name=channel)['id']

        bot.client.send_message(channel_id, text)


if __name__ == '__main__':
    bot.run()
