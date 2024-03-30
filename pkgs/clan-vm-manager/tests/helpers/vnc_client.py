#!/usr/bin/env python3

import os
from ctypes import (
    CDLL,
    POINTER,
    Structure,
    addressof,
    c_char_p,
    c_int,
    memmove,
    sizeof,
)
from pathlib import Path
from typing import TypeVar

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
    rfbCredentialTypeUser,
    rfbCredentialTypeX509,
    rfbGetClient,
    rfbInitClient,
    struct__rfbClient,
)

path_to_lib = libvncclient._libs["libvncclient.so"].access["cdecl"]._name
if path_to_lib.startswith("/nix/store/"):
    print("Using libvncclient from nix store")
    exit(-1)


libc = CDLL("libc.so.6")  # Use the correct path for your libc


def alloc_str(data: str) -> c_char_p:
    bdata = data.encode("ascii")
    data_buf = libc.malloc(len(bdata) + 1)  # +1 for null terminator
    memmove(data_buf, bdata, len(bdata) + 1)
    return data_buf


StructType = TypeVar("StructType", bound="Structure")


def alloc_struct(data: StructType) -> int:
    data_buf = libc.malloc(sizeof(data))
    memmove(data_buf, addressof(data), sizeof(data))
    return data_buf


def get_credential(
    rfb_client: POINTER(struct__rfbClient),  # type: ignore[valid-type]
    credential_type: c_int,
) -> int | None:
    print(f"==> get_credential: {credential_type}")

    if credential_type == rfbCredentialTypeUser:
        creds = rfbCredential()
        username = os.environ.get("USER")
        if not username:
            print("ERROR: USER environment variable is not set")
            return None
        creds.userCredential.username = alloc_str(username)
        creds.userCredential.password = None
        creds_buf = alloc_struct(creds)

        # Return a integer to the creds obj
        return creds_buf

    if credential_type == rfbCredentialTypeX509:
        ca_dir = (
            Path(os.environ.get("GIT_ROOT", ""))
            / "pkgs"
            / "clan-vm-manager"
            / "tests"
            / "data"
            / "vnc-security"
        )
        ca_cert = ca_dir / "ca.crt"
        if not ca_cert.exists():
            print(f"ERROR: ca_cert does not exist: {ca_cert}")
            return None
        ca_crl = ca_dir / "ca.key"
        if not ca_crl.exists():
            print(f"ERROR: ca_crl does not exist: {ca_crl}")
            return None

        # Instantiate the credential union and populate it
        creds = rfbCredential()
        creds.x509Credential.x509CACertFile = alloc_str(str(ca_cert))
        creds.x509Credential.x509CrlVerifyMode = False
        creds_buf = alloc_struct(creds)

        # Return a integer to the creds obj
        return creds_buf

    print(f"ERROR: Unknown credential type: {credential_type}")
    return None


def got_selection(cl: rfbClient, text: str, text_len: int) -> None:
    print(f"got_selection: {text}")


def resize(client: rfbClient) -> bool:
    print("===>resize")
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
