from __future__ import annotations

import dataclasses
import os
import shlex
import sys
from collections.abc import Callable
from typing import (
    Any,
    Optional,
    Type,
    TypeVar,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

if sys.version_info < (3, 11):
    from typing_extensions import (  # pytype: disable=not-supported-yet
        dataclass_transform,
    )
else:
    from typing import dataclass_transform

PRIMITIVE_TYPES = {int, float, str}

_T = TypeVar("_T")

READENV_METADATA_KEY = "readenv"


def _parse_dotenv(dotenv_file_path: str) -> dict[str, str]:
    """Parse a .env file into a dict

    Parameters
    ----------
    dotenv_file_path : str
        The path to the .env file

    Returns
    -------
    dict[str, str]
        The parsed key value pairs
    """
    vars: dict[str, str] = {}
    with open(dotenv_file_path) as f:
        dotenv = f.read()
        s = shlex.shlex(dotenv, posix=True)
        parts = list(s)
        for index, elem in enumerate(parts):
            if elem == "=":
                if 0 < index < len(parts):
                    if len(parts[index - 1]) > 0:
                        key = parts[index - 1]
                        value = parts[index + 1]
                        vars[key] = value
    return vars


@dataclasses.dataclass
class _FieldMetadata:
    file_location: Optional[str] = None
    file_name: Optional[str] = None
    file_path: Optional[str] = None
    env_name: Optional[str] = None
    dotenv_name: Optional[str] = None
    use_env: bool = True
    use_file: bool = True
    conversion_func: Optional[Callable[[str], Any]] = None


def field(
    *,
    file_location: Optional[str] = None,
    file_name: Optional[str] = None,
    file_path: Optional[str] = None,
    env_name: Optional[str] = None,
    dotenv_name: Optional[str] = None,
    use_env=True,
    use_file=True,
    conversion_func: Optional[Callable[[str], Any]] = None,
    **kwargs: Any,
) -> Any:
    """Configure field metadata

    Parameters
    ----------
    metadata : Optional[Dict[str, Any]], optional
        dataclass metadata dict if already one exists. Can be omitted if dataclass is
        not annotated with another library modifying the dataclass metadata,
        by default None
    file_location : Optional[str], optional
        Override the default file location for this field, by default None
    file_name : Optional[str], optional
        Override the file name for this field. Per default the lower case field name is
        used as file name, by default None
    file_path : Optional[str], optional
        Override the file path (constructed from file_location and file_name). Can be
        used instead of specifying file_location and file_name, by default None
    env_name : Optional[str], optional
        Override the name of the environment variable used to lookup this field. Per
        default the upper case field name is used as environment variable,
        by default None
    dotenv_name : Optional[str], optional
        Override the name of the dotenv variable used to lookup this field.
        Per default the upper case field name is used as environment variable,
        by default None
    use_env : bool, optional
        Use os.environ to look for variables, by default True
    use_file : bool, optional
        Use files to look for variables, by default True
    conversion_func : Optional[Callable[[str], Any]], optional
        Optional conversion function to convert complex types., by default None

    Returns
    -------
    Dict[Any, Any]
        The metadata dict for the dataclass
    """
    return dataclasses.field(
        metadata={
            READENV_METADATA_KEY: _FieldMetadata(
                file_location=file_location,
                file_name=file_name,
                file_path=file_path,
                env_name=env_name,
                dotenv_name=dotenv_name,
                use_env=use_env,
                use_file=use_file,
                conversion_func=conversion_func,
            )
        },
        **kwargs,
    )


@dataclass_transform(kw_only_default=True, field_descriptors=(field,))
def environment(cls: _T, **kwargs: Any) -> _T:
    if sys.version_info >= (3, 10):
        if kwargs is None:
            kwargs = {"kw_only": True}
        else:
            kwargs["kw_only"] = True
    return dataclasses.dataclass(**kwargs)(cls)


def is_optional_type(field) -> bool:
    """Returns True if field is Optional[X] type"""
    return get_origin(field) is Union and type(None) in get_args(field)


def get_type_of_optional(field) -> Any:
    """Get the X type of Optional[X]"""
    if not is_optional_type(field):
        raise ValueError("Field is not of Optional[x] type.")
    optional_types = set(get_args(field)) - {type(None)}
    if len(optional_types) > 1:
        raise ValueError("Optional[Union[]] types are not supported")
    return next(iter(optional_types))


def default_parse_bool_func(value: str) -> bool:
    """Default function to parse bool values"""
    if value.lower() in ("true", "1"):
        return True
    if value.lower() in ("false", "0"):
        return False
    raise RuntimeError(f"Can't parse {value} as bool.")


def read(
    cls: Type[_T],
    *,
    default_files_location: str = "/run/secrets",
    dotenv_path: Optional[str] = None,
) -> _T:
    """Read configurations from environment variables or files

    Parameters
    ----------
    cls : Type[T]
        A dataclass specifying the configuration to read
    default_files_location : str, optional
        The location where files are searched, by default "/run/secrets"
    dotenv_path : Optional[str], optional
        The path to a .env file, by default None

    Returns
    -------
    T
        The dataclass filled with data from the environment or files

    Raises
    ------
    RuntimeError
        When an error occurred while reading the data
    """

    # Parse dotenv file
    dotenv = None
    if dotenv_path is not None and os.path.exists(dotenv_path):
        dotenv = _parse_dotenv(dotenv_path)

    init_kwargs = {}
    types = get_type_hints(cls)

    for field in dataclasses.fields(cls):
        field_name = field.name
        field_type = types[field.name]

        if field_type == Ellipsis:
            field_type = str

        # Handle Optional[X] case
        if is_optional_type(field_type):
            type_ = get_type_of_optional(field_type)
        else:
            type_ = field_type

        # Field Metadata
        if READENV_METADATA_KEY in field.metadata:
            field_metadata: _FieldMetadata = field.metadata[READENV_METADATA_KEY]
        else:
            field_metadata = _FieldMetadata()

        # Determine if files or environment should be used
        read_file = True and field_metadata.use_file
        read_env = True and field_metadata.use_env

        raw_value = None
        value = None
        # Read from file
        if read_file:
            if field_metadata.file_path:
                file_path = field_metadata.file_path
            else:
                if field_metadata.file_location:
                    location = field_metadata.file_location
                else:
                    location = default_files_location

                if field_metadata.file_name:
                    file_name = field_metadata.file_name
                else:
                    file_name = field_name.lower()

                file_path = os.path.join(location, file_name)

            if os.path.exists(file_path):
                with open(file_path) as f:
                    raw_value = f.read().strip()

        # Read from dotenv
        if dotenv is not None and raw_value is None:
            if field_metadata.dotenv_name:
                dotenv_key = field_metadata.dotenv_name
            else:
                dotenv_key = field_name.upper()
            if dotenv_key in dotenv:
                raw_value = dotenv[dotenv_key]

        # Read from environment
        if read_env:
            if raw_value is None:
                if field_metadata.env_name:
                    environ_key = field_metadata.env_name
                else:
                    environ_key = field_name.upper()
                if environ_key in os.environ:
                    raw_value = os.environ[environ_key]

        # Convert raw values
        if raw_value is not None:
            try:
                if field_metadata.conversion_func is not None:
                    value = field_metadata.conversion_func(raw_value)
                elif type_ in PRIMITIVE_TYPES:
                    value = type_(raw_value)
                elif type_ == bool:
                    value = default_parse_bool_func(raw_value)
                elif type_ == Ellipsis:
                    value = str(raw_value)
                else:
                    raise RuntimeError(
                        "Not possible to convert type. "
                        f"Please specify conversion_func for field '{field.name}'."
                    )
            except Exception as e:
                raise RuntimeError(
                    f"Failed to convert value for field {field.name}: {e}"
                )

        # Use default value if None was previously found
        if value is None and not field.default == dataclasses.MISSING:
            value = field.default
        elif value is None and not field.default_factory == dataclasses.MISSING:
            value = field.default_factory()

        # Check if value is required and is not defined as Optional
        if value is None and not is_optional_type(field_type):
            raise RuntimeError(
                f"Field '{field_name}' is required but no value was found."
            )

        init_kwargs[field_name] = value

    return cls(**init_kwargs)
