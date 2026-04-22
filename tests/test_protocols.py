"""Tests for the protocol layer."""
import asyncio
import base64
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "api"))

# Point allowed roots at a temp dir for these tests
import os

TMP = tempfile.mkdtemp()
os.environ["ALLOWED_LOCAL_ROOTS"] = TMP
# Force reload of settings
import importlib
import config
importlib.reload(config)

from protocols.file_protocol import FileProtocol
from protocols.data_protocol import DataProtocol


def test_data_uri_plain():
    proto = DataProtocol()
    r = asyncio.get_event_loop().run_until_complete(
        proto.fetch("data:text/plain,hello%20world")
    )
    assert r.content == b"hello world"
    assert r.mime == "text/plain"


def test_data_uri_base64():
    payload = base64.b64encode(b"hi").decode()
    proto = DataProtocol()
    r = asyncio.get_event_loop().run_until_complete(
        proto.fetch(f"data:application/octet-stream;base64,{payload}")
    )
    assert r.content == b"hi"


def test_file_protocol_rejects_outside_root():
    proto = FileProtocol()
    with pytest.raises(PermissionError):
        asyncio.get_event_loop().run_until_complete(
            proto.fetch("file:///etc/passwd")
        )


def test_file_protocol_reads_inside_root():
    f = Path(TMP) / "x.txt"
    f.write_text("hello")
    proto = FileProtocol()
    r = asyncio.get_event_loop().run_until_complete(
        proto.fetch(f"file://{f}")
    )
    assert r.content == b"hello"
