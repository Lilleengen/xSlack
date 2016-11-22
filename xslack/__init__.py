#!/usr/bin/python

import sys
import json
from .xslack import init

def main():
    config = json.load(open(sys.argv[1], 'r'))
    init(config)
