#!/usr/bin/env bash

set -euo pipefail

#######################
#
# Use https://github.com/ctypesgen/ctypesgen to generate python bindings for libvncclient
#
#######################

# Check if the variable hardeningDisabled is set to "all"
if [ -z ${hardeningDisabled+x} ]; then
    echo "Hardening is enabled. Plase set hardeningDisabled to 'all' in the shell.nix file"
    exit 1
fi

OUT_PATH=$GIT_ROOT/pkgs/clan-vm-manager/tests/helpers/libvncclient.py
python3 ~/Projects/ctypesgen/run.py -l libvncclient.so "$LIBVNC_INCLUDE/rfb/rfbclient.h" -o "$OUT_PATH"