# envee

![Build status](https://github.com/c-technology/envee/actions/workflows/check.yml/badge.svg?branch=main)

Read variables from the environment or files into dataclasses.

While it is convenient to configure applications using environment variables during development, it is advised not to store sensitive information such as passwords in environment variables in production environments. The `envee` library allows reading variables either from the environment variables or files (which are typically used by e.g. [docker secrets](https://docs.docker.com/engine/swarm/secrets/)), thus keeping code used for development and production environments as close to each other as possible.

## Usage

Variables to read from the environment are declared using classes annotated with the `@envee.environment` decorator. Using `envee.read()` the fields of the classes are filled using the environment.

Example:

```python
from typing import Optional
import envee

@envee.environment
class Environment:
    username: str
    debug: Optional[str]
    workers: int = 5

env = envee.read(Environment)

```

### Environment variables names and file paths

For each field, per default `envee` looks for environment variables with the upper case name of the field. The corresponding file is looked in the directory `/run/secrets` and has the lower case field name as filename. If a corresponding file is found, the file will take precedence over an environment variable. For the example above, the `read()` method looks for the environment variables `USERNAME`, `DEBUG`, and `WORKERS`, respectively the files `/run/secrets/username`, `/run/secrets/debug`, and `/run/secrets/workers`.

### Types

Variables are typed using the dataclasses. Primitive types such as `int`, `float`, or `str` are automatically converted while reading. For more complex types, a conversion function needs to be provided. If fields are typed as `Optional`, their value will be set to `None` if no variable is found. If a default value is defined, this value will be used when no corresponding environment variable or file is found. Otherwise, when no environment variable is found and the field is not typed as `Optional`, a `RuntimeError` is raised.

### dotenv (.env) support

`envee` provides rudimentary support for `.env` files. Currently, the path to the `.env` file must be specified in the `read()` method. The name of the variable name must be the upper case name of the field name. Comments and multiline variables are supported. Variables found in a `.env` file take precedence over environment variables but not files.

The following `.env` file can be read using the following Python code:

```
DEBUG="True" # a comment
WORKERS=5
MULTILINE="first
second
3"
```

```python
@envee.environment
class Environment:
    debug: str
    workers: int
    multiline: str

env = envee.read(Environment, dotenv_path="/path/to/.env/file")
```

## Advanced usage

### Override environment variable names

In the following example the field debug is filled using the environment variable `PROJECT_DEBUG`.

```python
import envee

@envee.environment
class Environment:
    debug: str = envee.field(env_name="PROJECT_DEBUG")

env = envee.read(Environment)
```

### Override file locations

The default location can be changed by passing a different location to the `read()` method.

```python
import envee

@envee.environment
class Environment:
    debug: str

env = envee.read(Environment, default_files_location="/path/to/a/directory")
```

Alternatively, the fields metadata can specify the `file_location` or `file_name`. The parameter `file_location` overrides `default_files_location`. `file_name` overrides the default file name. The direct path to a file can be specified using `file_path`. `file_path` will take precedence over `file_location` or `file_name`.

```python
import envee

@envee.environment
class Environment:
    debug: str = envee.field(file_location="/other/dir", file_name="DEBUG.txt")

env = envee.read(Environment)
```

### Complex datatypes

For complex datatypes, a conversion function needs to be passed to the field.

```python
import envee

@envee.environment
class Environment:
    timestamp: datetime.datetime = envee.field(
        conversion_func=lambda x: datetime.datetime.fromisoformat(x)
    )


env = envee.read(Environment)
```
