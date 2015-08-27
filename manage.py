#!/usr/bin/env python
# coding: utf-8

import click
from mybot import bot


@click.group(context_settings={
    'help_option_names': ['-h', '--help']
})
def cli():
    """The commandline interface for raindrop mesos project"""
    pass


@cli.command()
def run():
    """Run slackbot service
    """
    from slackbot import app

    app.main()


@cli.command()
def show_channels():

    print ', '.join(i['name'] for i in bot.channels.itervalues())


@cli.command()
@click.argument('channel')
@click.argument('text')
def send_message(channel, text):
    bot.send_message(text, channel_name=channel)

if __name__ == '__main__':
    cli()
