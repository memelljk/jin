#!/usr/bin/env python
# coding: utf-8

import click


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
    from slackbot.core import get_channels

    print ', '.join(i['name'] for i in get_channels().itervalues())

if __name__ == '__main__':
    cli()
