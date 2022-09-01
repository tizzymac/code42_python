import logging
import sys
import warnings
from io import IOBase
from pathlib import Path
from typing import Union

from pydantic import BaseSettings
from pydantic import Field
from pydantic import root_validator
from pydantic import SecretStr
from pydantic import validator
from rich import pretty
from rich.console import Console
from rich.logging import RichHandler

from incydr.enums import _Enum


class LogLevel(_Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    WARN = "WARN"
    INFO = "INFO"
    DEBUG = "DEBUG"


# capture default displayhook so we can "uninstall" rich
_sys_displayhook = sys.displayhook


_std_log_formatter = logging.Formatter(
    fmt="%(asctime)s - %(name)s:%(levelname)s - %(message)s", datefmt="[%x %X]"
)
_rich_log_formatter = logging.Formatter(fmt="%(message)s", datefmt="[%x %X]")
_log_level_map = {"ERROR": 40, "WARNING": 30, "WARN": 30, "INFO": 20, "DEBUG": 10}
_custom_log_warning = "Custom logger detected, '{}' setting on `incydr.Client` will not apply to custom logger."


class IncydrSettings(BaseSettings):
    """
    Configure settings on the `incydr.Client`.

    Usage:

        >> import incydr
        >>> client = incydr.Client()
        >>> client.settings.page_size = 10

    Settings can also be loaded from shell environment variables or .env files. Just prefix a setting's attribute name
    with `INCYDR_` when configuring via enviroment vars.

    For example: To load `client.settings.api_client_secret` from the environment, set
    `INCYDR_API_CLIENT_SECRET="my_secret"`.

    The `incydr.Client` loads settings in the following priority:

    - Args passed to `Client` constructor
    - Shell environment variables
    - An .env file in the current working directory
    - An .env file in `~/.config/incydr` directory

    **Attributes**:

    * **api_client_id**: `str` The API Client Identifier for authentication. env_var=`INCYDR_API_CLIENT_ID`
    * **api_client_secret**: `str` The API Client Secret for authentication. env_var=`INCYDR_API_CLIENT_SECRET`
    * **url**: `str` The URL of your Code42 API gateway instance. env_var=`INCYDR_URL`
    * **page_size**: `int` The default page size for all paginated requests. Defaults to 100. env_var=`INCYDR_PAGE_SIZE`
    * **max_response_history**: `int` The maximum number of responses the `incydr.Client.response_history` list will
        store. Defaults to 5. env_var=`INCYDR_MAX_RESPONSE_HISTORY`
    * **log_file**: `str` The file path or file-liek object to write log output to. Defaults to None.
    * **log_level**: `int` The level for logging messages. Defaults to `logging.WARNING`. env_var=`INCYDR_LOG_LEVEL`
    * **logger**: `logging.Logger` The logger used for client logging. Can be replaced with a custom `logging.Logger`.
        Default logging goes to `sys.stderr`.
    * **user_agent_prefix**: `str` Prefixes all `User-Agent` headers with the supplied string.
    * **use_rich**: `bool` Enables [rich](https://rich.readthedocs.io/en/stable/introduction.html) support in logging
        and the Python repl. Defaults to True. env_var=`INCYDR_USE_RICH`
    """

    api_client_id: str = Field(env="incydr_api_client_id")
    api_client_secret: SecretStr = Field(env="incydr_api_client_secret")
    url: str = Field(env="incydr_url")
    page_size: int = Field(default=100, env="incydr_page_size")
    max_response_history: int = Field(default=5, env="incydr_max_response_history")
    use_rich: bool = Field(default=True, env="incydr_use_rich")
    log_stderr: bool = Field(default=True, env="incydr_log_stderr")
    log_file: Union[str, Path, IOBase] = Field(default=None, env="incydr_log_file")
    log_level: Union[int, str] = Field(
        default=logging.WARNING,
        env="incydr_log_level",
    )
    logger: logging.Logger = None
    user_agent_prefix: str = Field(default=None, env="incydr_user_agent_prefix")

    def __init__(self, **kwargs):
        # clear any keys from kwargs that are passed as None, which forces lookup of values
        kwargs = {k: v for k, v in kwargs.items() if v is not None}

        # if .env file in CWD, use it instead of ~/.config/incydr/.env
        if Path(".env").exists():
            kwargs["_env_file"] = ".env"
        super().__init__(**kwargs)

    class Config:
        env_file = str(Path.home() / ".config" / "incydr" / ".env")
        validate_assignment = True
        custom_logger = False

    @validator("log_level", pre=True, always=True)
    def _validate_log_level(cls, value, **kwargs):
        try:
            return int(value)
        except ValueError:
            value = value.upper()
            LogLevel(value)
            return _log_level_map[value]

    @validator("log_file")
    def _validate_log_file(cls, value, **kwargs):
        if isinstance(value, (str, Path)):
            p = Path(value)
            # existing file OK
            if p.exists() and p.is_file():
                value = str(p.absolute())
            # new file in existing dir OK
            elif not p.exists() and p.parent.is_dir():
                value = str(p.absolute())
            else:
                raise ValueError(f"{value} is not a valid file path for logging.")
        return value

    @validator("use_rich")
    def _validate_use_rich(cls, value, **kwargs):
        if value:
            pretty.install(max_length=2)
        else:
            sys.displayhook = _sys_displayhook
        return value

    @validator("logger")
    def _validate_logger(cls, value, **kwargs):
        if value is None:
            logger = logging.getLogger("incydr")
            # flag the logger we create with a custom attribute so we can detect user-provided loggers later
            logger._incydr = True
            return logger
        if isinstance(value, logging.Logger):
            return value
        else:
            raise ValueError(f"{value} is not a `logging.Logger`.")

    @root_validator(skip_on_failure=True)
    def configure_logging(cls, values):
        use_rich = values["use_rich"]
        log_file = values["log_file"]
        log_stderr = values["log_stderr"]
        log_level = values["log_level"]
        logger = values["logger"]

        if not hasattr(logger, "_incydr"):
            warnings.warn(
                "A custom logger has been set, all other log-related settings on the `incydr.Client` are ignored for custom loggers."
            )
            return values

        logger.handlers.clear()

        if log_stderr and use_rich:
            console = Console(stderr=True)
            rich_handler = RichHandler(console=console, rich_tracebacks=True)
            rich_handler.setFormatter(_rich_log_formatter)
            logger.addHandler(rich_handler)

        if log_stderr and not use_rich:
            std_handler = logging.StreamHandler()
            std_handler.setFormatter(_std_log_formatter)
            logger.addHandler(std_handler)

        if log_file and use_rich:
            if isinstance(log_file, str):
                log_file = open(log_file, "a", encoding="utf-8")
            console = Console(file=log_file, no_color=True, width=200)
            rich_file_handler = RichHandler(console=console, rich_tracebacks=True)
            rich_file_handler.setFormatter(_rich_log_formatter)
            logger.addHandler(rich_file_handler)

        if log_file and not use_rich:
            if isinstance(log_file, str):
                std_file_handler = logging.FileHandler(
                    filename=log_file, encoding="utf-8"
                )
            else:
                std_file_handler = logging.StreamHandler(stream=log_file)
            std_file_handler.setFormatter(_std_log_formatter)
            logger.addHandler(std_file_handler)

        logger.setLevel(log_level)
        values["logger"] = logger
        return values

    # @validator("logger")
    # def _validate_logger(cls, value, values, config, **kwargs):
    #     if value is None:
    #         return configure_logger(**values)
    #     if isinstance(value, logging.Logger):
    #         config.custom_logger = True
    #     if not isinstance(value, logging.Logger):
    #         raise ValueError(f"{value} is not a logging.Logger")
    #     return value


def configure_logger(
    logger: logging.Logger = None,
    log_file: Union[str, IOBase] = None,
    use_rich: bool = True,
    log_level: int = 40,
    log_stderr: bool = True,
    **kwargs,
):
    if logger is None:
        logger = logging.getLogger("incydr")
    logger.handlers.clear()

    if log_stderr and use_rich:
        console = Console(stderr=True)
        rich_handler = RichHandler(console=console, rich_tracebacks=True)
        rich_handler.setFormatter(_rich_log_formatter)
        logger.addHandler(rich_handler)

    if log_stderr and not use_rich:
        std_handler = logging.StreamHandler()
        std_handler.setFormatter(_std_log_formatter)
        logger.addHandler(std_handler)

    if log_file and use_rich:
        if isinstance(log_file, str):
            file = open(log_file, "a", encoding="utf-8")
        else:
            file = log_file
        console = Console(file=file, no_color=True, width=200)
        rich_file_handler = RichHandler(console=console, rich_tracebacks=True)
        rich_file_handler.setFormatter(_rich_log_formatter)
        logger.addHandler(rich_file_handler)

    if log_file and not use_rich:
        if isinstance(log_file, str):
            std_file_handler = logging.FileHandler(filename=log_file, encoding="utf-8")
        else:
            std_file_handler = logging.StreamHandler(stream=log_file)
        std_file_handler.setFormatter(_std_log_formatter)
        logger.addHandler(std_file_handler)

    logger.setLevel(log_level)
    return logger
