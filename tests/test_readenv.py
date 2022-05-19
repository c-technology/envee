import datetime
import os
from dataclasses import dataclass, field
from typing import List, Optional

import pytest

from readenv import environment, metadata


def test_read_env(monkeypatch):
    @environment
    @dataclass
    class Environment:
        debug: str

    monkeypatch.setenv("DEBUG", "true")
    env = Environment.read()

    assert env.debug == "true"


def test_read_env_rename(monkeypatch):
    @environment
    @dataclass
    class Environment:
        debug: str = field(metadata=metadata(env_name="DEBUG2"))

    monkeypatch.setenv("DEBUG2", "true")
    env = Environment.read()

    assert env.debug == "true"


def test_read_env_complex(monkeypatch):
    @environment
    @dataclass
    class Environment:
        timestamp: datetime.datetime = field(
            metadata=metadata(conversion_func=lambda x: datetime.datetime.fromisoformat(x))
        )

    monkeypatch.setenv("TIMESTAMP", "2022-05-18T16:10:41.156832")
    env = Environment.read()

    assert env.timestamp == datetime.datetime(2022, 5, 18, 16, 10, 41, 156832)


def test_read_env_wrong_type(monkeypatch):
    @environment
    @dataclass
    class Environment:
        debug: int

    monkeypatch.setenv("DEBUG", "true")

    with pytest.raises(RuntimeError):
        Environment.read()


def test_read_env_default():
    @environment
    @dataclass
    class Environment:
        debug: str = "false"

    env = Environment.read()
    assert env.debug == "false"


def test_read_env_default_factory():
    @environment
    @dataclass
    class Environment:
        debug: List[str] = field(default_factory=list)

    env = Environment.read()
    assert env.debug == []


def test_read_env_optional():
    @environment
    @dataclass
    class Environment:
        debug: Optional[str]

    env = Environment.read()
    assert env.debug == None


def test_read_file_path(tmpdir):
    p = tmpdir.mkdir("secrets").join("debug")
    p.write("true")

    assert "DEBUG" not in os.environ

    @environment
    @dataclass
    class Environment:
        debug: str = field(metadata=metadata(file_path=p.realpath()))

    env = Environment.read()
    assert env.debug == "true"


def test_read_file_location(tmpdir):
    p_dir = tmpdir.mkdir("secrets")
    p = p_dir.join("debug")
    p.write("true")

    assert "DEBUG" not in os.environ

    @environment
    @dataclass
    class Environment:
        debug: str = field(metadata=metadata(file_location=p_dir.realpath()))

    env = Environment.read()
    assert env.debug == "true"


def test_read_default_location(tmpdir):
    p_dir = tmpdir.mkdir("secrets")
    p = p_dir.join("debug")
    p.write("true")

    assert "DEBUG" not in os.environ

    @environment
    @dataclass
    class Environment:
        debug: str

    env = Environment.read(default_location=p_dir.realpath())
    assert env.debug == "true"



def test_read_file_location_and_file_name(tmpdir):
    p_dir = tmpdir.mkdir("secrets")
    p = p_dir.join("debug2")
    p.write("true")

    assert "DEBUG" not in os.environ

    @environment
    @dataclass
    class Environment:
        debug: str = field(metadata=metadata(file_location=p_dir.realpath(), file_name="debug2"))

    env = Environment.read()
    assert env.debug == "true"


def test_read_only_env(monkeypatch, tmpdir):

    p_dir = tmpdir.mkdir("secrets")
    p = p_dir.join("debug")
    p.write("false")

    @environment
    @dataclass
    class Environment:
        debug: str = field(metadata=metadata(file_location=p_dir.realpath(), only_env=True))

    monkeypatch.setenv("DEBUG", "true")
    env = Environment.read()

    assert env.debug == "true"


def test_read_only_file(monkeypatch, tmpdir):

    p_dir = tmpdir.mkdir("secrets")
    p = p_dir.join("debug")
    p.write("false")

    @environment
    @dataclass
    class Environment:
        debug: str = field(metadata=metadata(file_location=p_dir.realpath(), only_file=True))

    monkeypatch.setenv("DEBUG", "true")
    env = Environment.read()

    assert env.debug == "false"


def test_read_default_type(monkeypatch):

    @environment
    @dataclass
    class Environment:
        debug: ...

    monkeypatch.setenv("DEBUG", "true")
    env = Environment.read()

    assert type(env.debug) == str and env.debug == "true"
