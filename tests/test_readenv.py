import datetime
import os
import pathlib
from typing import List, Optional

import pytest

import readenv


def test_read_env(monkeypatch):
    @readenv.environment
    class Environment:
        debug: str

    monkeypatch.setenv("DEBUG", "true")
    env = readenv.read(Environment)

    assert env.debug == "true"


def test_read_env_rename(monkeypatch):
    @readenv.environment
    class Environment:
        debug: str = readenv.field(env_name="DEBUG2")

    monkeypatch.setenv("DEBUG2", "true")
    env = readenv.read(Environment)

    assert env.debug == "true"


def test_read_env_complex(monkeypatch):
    @readenv.environment
    class Environment:
        timestamp: datetime.datetime = readenv.field(
            conversion_func=lambda x: datetime.datetime.fromisoformat(x)
        )

    monkeypatch.setenv("TIMESTAMP", "2022-05-18T16:10:41.156832")
    env = readenv.read(Environment)

    assert env.timestamp == datetime.datetime(2022, 5, 18, 16, 10, 41, 156832)


def test_read_env_wrong_type(monkeypatch):
    @readenv.environment
    class Environment:
        debug: int

    monkeypatch.setenv("DEBUG", "true")

    with pytest.raises(RuntimeError):
        readenv.read(Environment)


def test_read_env_default():
    @readenv.environment
    class Environment:
        debug: str = "false"

    env = readenv.read(Environment)
    assert env.debug == "false"


def test_read_env_default_factory():
    @readenv.environment
    class Environment:
        debug: List[str] = readenv.field(default_factory=list)

    env = readenv.read(Environment)
    assert env.debug == []


def test_read_env_optional():
    @readenv.environment
    class Environment:
        debug: Optional[str]

    env = readenv.read(Environment)
    assert env.debug == None


def test_read_file_path(tmpdir):
    p = tmpdir.mkdir("secrets").join("debug")
    p.write("true")

    assert "DEBUG" not in os.environ

    @readenv.environment
    class Environment:
        debug: str = readenv.field(file_path=p.realpath())

    env = readenv.read(Environment)
    assert env.debug == "true"


def test_read_file_location(tmpdir):
    p_dir = tmpdir.mkdir("secrets")
    p = p_dir.join("debug")
    p.write("true")

    assert "DEBUG" not in os.environ

    @readenv.environment
    class Environment:
        debug: str = readenv.field(file_location=p_dir.realpath())

    env = readenv.read(Environment)
    assert env.debug == "true"


def test_read_default_location(tmpdir):
    p_dir = tmpdir.mkdir("secrets")
    p = p_dir.join("debug")
    p.write("true")

    assert "DEBUG" not in os.environ

    @readenv.environment
    class Environment:
        debug: str

    env = readenv.read(Environment, default_files_location=p_dir.realpath())
    assert env.debug == "true"


def test_read_file_location_and_file_name(tmpdir):
    p_dir = tmpdir.mkdir("secrets")
    p = p_dir.join("debug2")
    p.write("true")

    assert "DEBUG" not in os.environ

    @readenv.environment
    class Environment:
        debug: str = readenv.field(file_location=p_dir.realpath(), file_name="debug2")

    env = readenv.read(Environment)
    assert env.debug == "true"


def test_read_only_env(monkeypatch, tmpdir):

    p_dir = tmpdir.mkdir("secrets")
    p = p_dir.join("debug")
    p.write("false")

    @readenv.environment
    class Environment:
        debug: str = readenv.field(
            file_location=p_dir.realpath(), use_env=True, use_file=False
        )

    monkeypatch.setenv("DEBUG", "true")
    env = readenv.read(Environment)

    assert env.debug == "true"


def test_read_only_file(monkeypatch, tmpdir):

    p_dir = tmpdir.mkdir("secrets")
    p = p_dir.join("debug")
    p.write("false")

    @readenv.environment
    class Environment:
        debug: str = readenv.field(
            file_location=p_dir.realpath(), use_env=False, use_file=True
        )

    monkeypatch.setenv("DEBUG", "true")
    env = readenv.read(Environment)

    assert env.debug == "false"


def test_read_default_type(monkeypatch):
    @readenv.environment
    class Environment:
        debug: ...

    monkeypatch.setenv("DEBUG", "true")
    env = readenv.read(Environment)

    assert type(env.debug) == str and env.debug == "true"


def test_read_int_and_float(monkeypatch):
    @readenv.environment
    class Environment:
        an_int: int
        a_float: float

    monkeypatch.setenv("AN_INT", "42")
    monkeypatch.setenv("A_FLOAT", "100.0")
    env = readenv.read(Environment)

    assert env.an_int == 42
    assert env.a_float == 100.0


def test_read_dotenv(tmp_path: pathlib.Path):

    dotenv_file = tmp_path / ".env"
    dotenv_file.write_text(
        'DEBUG="True" #a comment\nWORKERS=5\nmultiline="first\nsecond\n3"'
    )

    @readenv.environment
    class Environment:
        debug: str
        workers: int
        multiline: str = readenv.field(dotenv_name="multiline")

    env = readenv.read(Environment, dotenv_path=dotenv_file.absolute())

    assert env.debug == "True"
    assert env.workers == 5
    assert env.multiline == "first\nsecond\n3"
