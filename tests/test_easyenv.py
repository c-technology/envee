import datetime
import os
import pathlib
import sys
from typing import List, Optional

import pytest

import easyenv


def test_read_env(monkeypatch):
    @easyenv.environment
    class Environment:
        debug: str

    monkeypatch.setenv("DEBUG", "true")
    env = easyenv.read(Environment)

    assert env.debug == "true"


def test_read_env_rename(monkeypatch):
    @easyenv.environment
    class Environment:
        debug: str = easyenv.field(env_name="DEBUG2")

    monkeypatch.setenv("DEBUG2", "true")
    env = easyenv.read(Environment)

    assert env.debug == "true"


def test_read_env_complex(monkeypatch):
    @easyenv.environment
    class Environment:
        timestamp: datetime.datetime = easyenv.field(
            conversion_func=lambda x: datetime.datetime.fromisoformat(x)
        )

    monkeypatch.setenv("TIMESTAMP", "2022-05-18T16:10:41.156832")
    env = easyenv.read(Environment)

    assert env.timestamp == datetime.datetime(2022, 5, 18, 16, 10, 41, 156832)


def test_read_env_wrong_type(monkeypatch):
    @easyenv.environment
    class Environment:
        debug: int

    monkeypatch.setenv("DEBUG", "true")

    with pytest.raises(RuntimeError):
        easyenv.read(Environment)


def test_read_env_default():
    @easyenv.environment
    class Environment:
        debug: str = "false"

    env = easyenv.read(Environment)
    assert env.debug == "false"


def test_read_env_default_factory():
    @easyenv.environment
    class Environment:
        debug: List[str] = easyenv.field(default_factory=list)

    env = easyenv.read(Environment)
    assert env.debug == []


def test_read_env_optional():
    @easyenv.environment
    class Environment:
        debug: Optional[str]

    env = easyenv.read(Environment)
    assert env.debug == None


def test_read_file_path(tmpdir):
    p = tmpdir.mkdir("secrets").join("debug")
    p.write("true")

    assert "DEBUG" not in os.environ

    @easyenv.environment
    class Environment:
        debug: str = easyenv.field(file_path=p.realpath())

    env = easyenv.read(Environment)
    assert env.debug == "true"


def test_read_file_location(tmpdir):
    p_dir = tmpdir.mkdir("secrets")
    p = p_dir.join("debug")
    p.write("true")

    assert "DEBUG" not in os.environ

    @easyenv.environment
    class Environment:
        debug: str = easyenv.field(file_location=p_dir.realpath())

    env = easyenv.read(Environment)
    assert env.debug == "true"


def test_read_default_location(tmpdir):
    p_dir = tmpdir.mkdir("secrets")
    p = p_dir.join("debug")
    p.write("true")

    p2 = p_dir.join("debug2")
    p2.write("false")

    assert "DEBUG" not in os.environ
    assert "DEBUG2" not in os.environ

    @easyenv.environment
    class Environment:
        debug: str
        DEBUG2: str

    env = easyenv.read(Environment, default_files_location=p_dir.realpath())
    assert env.debug == "true"
    assert env.DEBUG2 == "false"


def test_read_file_location_and_file_name(tmpdir):
    p_dir = tmpdir.mkdir("secrets")
    p = p_dir.join("debug2")
    p.write("true")

    assert "DEBUG" not in os.environ

    @easyenv.environment
    class Environment:
        debug: str = easyenv.field(file_location=p_dir.realpath(), file_name="debug2")

    env = easyenv.read(Environment)
    assert env.debug == "true"


def test_read_only_env(monkeypatch, tmpdir):

    p_dir = tmpdir.mkdir("secrets")
    p = p_dir.join("debug")
    p.write("false")

    @easyenv.environment
    class Environment:
        debug: str = easyenv.field(
            file_location=p_dir.realpath(), use_env=True, use_file=False
        )

    monkeypatch.setenv("DEBUG", "true")
    env = easyenv.read(Environment)

    assert env.debug == "true"


def test_read_only_file(monkeypatch, tmpdir):

    p_dir = tmpdir.mkdir("secrets")
    p = p_dir.join("debug")
    p.write("false")

    @easyenv.environment
    class Environment:
        debug: str = easyenv.field(
            file_location=p_dir.realpath(), use_env=False, use_file=True
        )

    monkeypatch.setenv("DEBUG", "true")
    env = easyenv.read(Environment)

    assert env.debug == "false"


def test_read_default_type(monkeypatch):
    @easyenv.environment
    class Environment:
        debug: ...

    monkeypatch.setenv("DEBUG", "true")
    env = easyenv.read(Environment)

    assert type(env.debug) == str and env.debug == "true"


def test_read_int_and_float(monkeypatch):
    @easyenv.environment
    class Environment:
        an_int: int
        a_float: float

    monkeypatch.setenv("AN_INT", "42")
    monkeypatch.setenv("A_FLOAT", "100.0")
    env = easyenv.read(Environment)

    assert env.an_int == 42
    assert env.a_float == 100.0


def test_read_dotenv(tmp_path: pathlib.Path):

    dotenv_file = tmp_path / ".env"
    dotenv_file.write_text(
        'DEBUG="True" #a comment\nWORKERS=5\nmultiline="first\nsecond\n3"'
    )

    @easyenv.environment
    class Environment:
        debug: str
        workers: int
        multiline: str = easyenv.field(dotenv_name="multiline")

    env = easyenv.read(Environment, dotenv_path=str(dotenv_file.absolute()))

    assert env.debug == "True"
    assert env.workers == 5
    assert env.multiline == "first\nsecond\n3"


@pytest.mark.parametrize(
    "env_value,expected",
    [
        ("1", True),
        ("True", True),
        ("true", True),
        ("0", False),
        ("False", False),
        ("false", False),
    ],
)
def test_parse_bool(monkeypatch, env_value: str, expected: bool):
    @easyenv.environment
    class Environment:
        debug: bool

    monkeypatch.setenv("DEBUG", env_value)

    env = easyenv.read(Environment)

    assert env.debug == expected


@pytest.mark.skipif(sys.version_info < (3, 10), reason="requires python3.10 or higher")
def test_default_fields_ordering(monkeypatch):
    @easyenv.environment
    class Environment:
        USER: str
        PASSWORD: str
        HOST: str
        PORT: int = 5432
        DB: str

    monkeypatch.setenv("USER", "user")
    monkeypatch.setenv("PASSWORD", "password")
    monkeypatch.setenv("HOST", "host")
    monkeypatch.setenv("DB", "db")

    env = easyenv.read(Environment)

    assert env.USER == "user"
    assert env.PASSWORD == "password"
    assert env.HOST == "host"
    assert env.PORT == 5432
    assert env.DB == "db"
