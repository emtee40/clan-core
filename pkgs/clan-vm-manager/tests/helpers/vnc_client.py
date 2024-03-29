#!/usr/bin/env python3

import os
from ctypes import byref, c_int
from pathlib import Path

import libvncclient
from libvncclient import (
    GetCredentialProc,
    GotFrameBufferUpdateProc,
    GotXCutTextProc,
    HandleKeyboardLedStateProc,
    HandleRFBServerMessage,
    MallocFrameBufferProc,
    String,
    WaitForMessage,
    rfbClient,
    rfbClientCleanup,
    rfbCredential,
    rfbCredentialTypeX509,
    rfbGetClient,
    rfbInitClient,
)

path_to_lib = libvncclient._libs["libvncclient.so"].access["cdecl"]._name
if path_to_lib.startswith("/nix/store/"):
    print("Using libvncclient from nix store")
    exit(-1)

credentials = {}


def get_credential(rfb_client: rfbClient, credential_type: int) -> rfbCredential:
    print(f"==> get_credential: {credential_type}")
    creds = rfbCredential()
    credentials[credential_type] = creds
    if credential_type != rfbCredentialTypeX509:
        print(f"Unknown credential type {credential_type}")
        return None

    git_root = os.environ.get("GIT_ROOT")
    assert git_root
    ca_path = (
        Path(git_root)
        / "pkgs"
        / "clan-vm-manager"
        / "tests"
        / "data"
        / "vnc-security"
        / "ca.crt"
    )
    if not ca_path.exists():
        print(f"ERROR: ca_path does not exist: {ca_path}")
        return None
    breakpoint()
    print(f"ca_path: {ca_path}")
    creds.x509Credential.x509CACertFile = String.from_param(str(ca_path))
    # creds.x509Credential.x509CACrlFile = String.from_param("A")
    # creds.x509Credential.x509ClientCertFile = String.from_param("B")
    # creds.x509Credential.x509ClientKeyFile = String.from_param("C")
    creds.x509Credential.x509CrlVerifyMode = False

    return byref(creds)


def got_selection(cl: rfbClient, text: str, text_len: int) -> None:
    print(f"got_selection: {text}")


def resize(client: rfbClient) -> bool:
    print("resize")
    return False


def update(cl: rfbClient, x: int, y: int, w: int, h: int) -> None:
    print(f"update: {x} {y} {w} {h}")


def kbd_leds(cl: rfbClient, value: int, pad: int) -> None:
    print(f"kbd_leds: {value} {pad}")


def main() -> None:
    bits_per_sample = 8
    samples_per_pixel = 3
    bytes_per_pixel = 4
    client: rfbClient = rfbGetClient(
        bits_per_sample, samples_per_pixel, bytes_per_pixel
    )
    if not client:
        print("rfbGetClient failed")
        exit(-1)

    # client settings
    client.contents.MallocFrameBuffer = MallocFrameBufferProc(resize)
    client.contents.canHandleNewFBSize = True
    client.contents.GotFrameBufferUpdate = GotFrameBufferUpdateProc(update)
    client.contents.HandleKeyboardLedState = HandleKeyboardLedStateProc(kbd_leds)
    client.contents.GotXCutText = GotXCutTextProc(got_selection)
    client.contents.GetCredential = GetCredentialProc(get_credential)
    client.contents.listenPort = 5900
    client.contents.listenAddress = String.from_param("127.0.0.1")

    print("Initializing connection")
    argc = c_int(0)
    argv = None
    if not rfbInitClient(client, argc, argv):
        print("rfbInitClient failed")
        exit(-1)

    while True:
        res = WaitForMessage(client, 500)
        if res < 0:
            rfbClientCleanup(client)
            print("WaitForMessage failed")
            exit(-1)

        if res > 0:
            if not HandleRFBServerMessage(client):
                rfbClientCleanup(client)
                print("HandleRFBServerMessage failed")
                exit(-1)


if __name__ == "__main__":
    main()
