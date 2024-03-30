#!/usr/bin/env bash


PYTHON_DIR=$(dirname "$(which python3)")/..
gdb --quiet -ex "source $PYTHON_DIR/share/gdb/libpython.py" -ex "run" -ex "b tls_openssl.c:618" --args python "$1"