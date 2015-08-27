#!/usr/bin/env python
# coding: utf-8

from slackbot.wsbot import WSBot
import mybot_config


bot = WSBot(mybot_config)


@bot.match_text(r'^/loki')
def hello(message):
    pass


if __name__ == '__main__':
    bot.run()
