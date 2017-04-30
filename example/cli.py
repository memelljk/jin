#!/usr/bin/env python
# coding: utf-8

import click


@click.group(context_settings={
    'help_option_names': ['-h', '--help']
})
def cli():
    """The commandline interface for raindrop mesos project"""
    pass


def _get_bot():
    from mybot import bot
    bot.prepare()
    return bot


@cli.command()
def show_channels():
    bot = _get_bot()
    print ', '.join('{name} ({id})'.format(**i) for i in bot.channels)


@cli.command()
@click.argument('channel')
@click.argument('text')
def send_message(channel, text):
    bot = _get_bot()
    bot.send_message(text, channel=channel)

if __name__ == '__main__':
    cli()
