# readenv

![Build status](https://github.com/c-technology/readenv/actions/workflows/check.yml/badge.svg?branch=main)

Read dataclasses from environment variables or files.

While it is convenient to configure applications using environment variables during development, it is advised not to store sensitive information such as passwords in environment variables in production environments. The `readenv` library allows reading variables either from the environment variables or files (which are typically used by e.g. [docker secrets](https://docs.docker.com/engine/swarm/secrets/)), thus keeping code used for development and production environments as close as possible.  


## Usage

To read environment variables, a `dataclass` is annotated with the `@environment` decorator. The environment is then read by calling the `read()` method on the dataclass. 

Variables are typed using the dataclasses. Primitive types such as `int`, `float`, or `str` are automatically converted while reading. For more complex types, a conversion function needs to be provided. If fields are typed as `Optional`, their value will be set to `None` if no variable is found. If a default value is defined, this value will be used when no corresponding environment variable or file is found. Otherwise, when no environment variable is found and the field is not typed as `Optional`, a `RuntimeError` is raised. 

For each field, per default `readenv` looks for environment variables with the upper case name of the field. The corresponding file is looked in the directory `/run/secrets` and has the lower case field name as filename. If a corresponding file is found, the file will take precedence over an environment variable. For the following example, `readenv` looks for the environment variables `USERNAME`, `DEBUG`, and `WORKERS`, respectively the files `/run/secrets/username`, `/run/secrets/debug`, and `/run/secrets/workers`. 
    
```python
from dataclasses import dataclass
from typing import Optional
from readenv import environment

@environment
@dataclass
class Environment:
    username: str
    debug: Optional[str]
    wokers: int = 5

env = Environment.read()

```


## Advanced usage

### Override environment variable names

In the following example the field debug is flled using the environment variable `PROJECT_DEBUG`.

```python
from dataclasses import dataclass, field
from readenv import environment, metadata

@environment
@dataclass
class Environment:
    debug: str = field(metadata=metadata(env_name="PROJECT_DEBUG"))

env = Environment.read()
```

### Override file locations

The default location can be changed by passing a different location to the `read()` method. 

```python
from dataclasses import dataclass, field
from readenv import environment, metadata

@environment
@dataclass
class Environment:
    debug: str

env = Environment.read(default_location="/other/dir")
```

Alternatively, the fields metadata can specify the `file_location` or `file_name`.  The parameter `file_location` overrides the default location and `file_name` overrides the file name. The direct path to a file can be specified using `file_path`. `file_path` will take precedence over `file_location` or `file_name`.

```python
from dataclasses import dataclass, field
from readenv import environment, metadata

@environment
@dataclass
class Environment:
    debug: str = field(metadata=metadata(file_location="/other/dir", file_name="DEBUG.txt"))

env = Environment.read()
```

### Complex datatypes

For complex datatypes, a conversion function needs to be passed to the field. 

```python
from dataclasses import dataclass, field
from readenv import environment, metadata

@environment
@dataclass
class Environment:
    timestamp: datetime.datetime = field(
            metadata=metadata(conversion_func=lambda x: datetime.datetime.fromisoformat(x))
        )

env = Environment.read()
```
