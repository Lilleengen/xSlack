#!/usr/bin/python

import json
import sys

from .xslack import add_token_channel, start


def main():
    config = json.load(open(sys.argv[1], 'r'))
    for channel in config["channels"]:
        for token in channel["tokens"]:
            add_token_channel(token, channel["name"])

    start()
