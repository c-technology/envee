import abc
import os
from dataclasses import MISSING, dataclass, fields
from typing import (
    Any,
    Callable,
    Dict,
    Optional,
    Type,
    TypeVar,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)


PRIMITIVE_TYPES = {bool, int, float, str, bytes}

T = TypeVar("T")

READENV_METADATA_KEY = "readenv"


@dataclass
class FieldMetadata:
    file_location: Optional[str] = None
    file_name: Optional[str] = None
    file_path: Optional[str] = None
    env_name: Optional[str] = None
    only_env: bool = False
    only_file: bool = False
    conversion_func: Optional[Callable[[str], Any]] = None


def metadata(
    *,
    metadata: Optional[Dict[str, Any]] = None,
    file_location: Optional[str] = None,
    file_name: Optional[str] = None,
    file_path: Optional[str] = None,
    env_name: Optional[str] = None,
    only_env=False,
    only_file=False,
    conversion_func: Optional[Callable[[str], Any]] = None,
) -> Dict[Any, Any]:
    """Configure field

    Parameters
    ----------
    metadata : Optional[Dict[str, Any]], optional
        dataclass metadata dict if already one exists. Can be omitted if dataclass is not annotated with another library modifying the dataclass metadata.
    file_location : Optional[str], optional
        Override the default file location for this field
    file_name : Optional[str], optional
        Override the file name for this field. Per default the lower case field name is used as file name.
    file_path : Optional[str], optional
        Override the file path (constructed from file_location and file_name). Can be used instead of specifying file_location and file_name.
    env_name : Optional[str], optional
        Override the name of the environment variable used to lookup this field. Per default the upper case field name is used as environment variable.
    only_env : bool, optional
        Only check environment variables for this field.
    only_file : bool, optional
        Only check files for this field.
    conversion_func : Optional[Callable[[str], Any]], optional
        Optional conversion function to convert complex types.

    Returns
    -------
    Dict[Any, Any]
        The metadata dict for the dataclass
    """
    if metadata is None:
        metadata = {}
    metadata[READENV_METADATA_KEY] = FieldMetadata(
        file_location=file_location,
        file_name=file_name,
        file_path=file_path,
        env_name=env_name,
        only_env=only_env,
        only_file=only_file,
        conversion_func=conversion_func,
    )
    return metadata


def environment(_cls=None):
    def wrap(cls):
        return _process_class(cls)

    if _cls is None:
        return wrap
    return wrap(_cls)


def _process_class(cls):
    cls.read = classmethod(EnvironmentReaderMixin.read.__func__)
    EnvironmentReaderMixin.register(cls)
    return cls


def is_optional_type(field):
    """Returns True if field Optional[X] type"""
    return get_origin(field) is Union and type(None) in get_args(field)


def get_type_of_optional(field) -> Any:
    """Get the X type of Optional[X]"""
    if not is_optional_type(field):
        raise ValueError("Field is not of Optional[x] type.")
    optional_types = set(get_args(field)) - {type(None)}
    if len(optional_types) > 1:
        raise ValueError("Optional[Union[]] types are not supported")
    return next(iter(optional_types))


class EnvironmentReaderMixin(abc.ABC):
    @classmethod
    def read(cls: Type[T], default_location="/run/secrets") -> T:
        """Load environment variables from os.environ and files

        Parameters
        ----------
        default_location : str, optional
            The location where files are searched, by default "/run/secrets"
        """

        init_kwargs = {}
        types = get_type_hints(cls)

        for field in fields(cls):
            field_name = field.name
            field_type = types[field.name]

            # Handle Optional[X] case
            if is_optional_type(field_type):
                type_ = get_type_of_optional(field_type)
            else:
                type_ = field_type

            # Field Metadata
            if READENV_METADATA_KEY in field.metadata:
                field_metadata: FieldMetadata = field.metadata[READENV_METADATA_KEY]
            else:
                field_metadata = FieldMetadata()

            read_file = True
            read_env = True
            if field_metadata.only_env:
                read_file = False
                read_env = True
            if field_metadata.only_file:
                read_file = True
                read_env = False

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
                        location = default_location

                    if field_metadata.file_name:
                        file_name = field_metadata.file_name
                    else:
                        file_name = field_name

                    file_path = os.path.join(location, file_name)

                if os.path.exists(file_path):
                    with open(file_path) as f:
                        raw_value = f.read().strip()

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
                    elif type_ == Ellipsis:
                        value = str(raw_value)
                    else:
                        raise RuntimeError(
                            f"Not possible to convert type. Please specify an appropriate a conversion_func for field '{field.name}'."
                        )
                except Exception as e:
                    raise RuntimeError(f"Failed to convert value for field {field.name}: {e}")

            # Use default value if None has previously found
            if value is None and not field.default == MISSING:
                value = field.default
            elif value is None and not field.default_factory == MISSING:
                value = field.default_factory()

            # Check if value is required and is not defined as Optional
            if value is None and not is_optional_type(field_type):
                raise RuntimeError(f"Field '{field_name}' is required but no value was found.")

            init_kwargs[field_name] = value

        return cls(**init_kwargs)  # type: ignore
