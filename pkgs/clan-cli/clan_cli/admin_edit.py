# !/usr/bin/env python3
import argparse

import argparse_schema


# takes a (sub)parser and configures it
def register_parser(parser: argparse.ArgumentParser) -> None:
    argparse_schema.register_parser(schema="./argument_config.json", parser=parser)
