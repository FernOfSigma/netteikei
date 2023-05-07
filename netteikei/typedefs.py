from collections.abc import (
    Callable,
    Iterable,
    Mapping
)
from typing import Any, Literal, TypedDict

from aiohttp import (
    BaseConnector,
    BasicAuth,
    ClientTimeout,
    HttpVersion,
    TraceConfig
)
from aiohttp.abc import AbstractCookieJar
from aiohttp.typedefs import StrOrURL
from multidict import istr


Method = Literal["POST", "GET", "PUT", "HEAD", "PATCH", "DELETE"]
Headers = Mapping[str, str]


# Wide type hints according to the aiohttp 3.8.4 documentation.
class SessionOpts(TypedDict, total=False):
    base_url: StrOrURL
    connector: BaseConnector
    cookies: dict[str, str]
    headers: Headers
    skip_auto_headers: Iterable[str | istr]
    auth: BasicAuth
    version: HttpVersion
    cookie_jar: AbstractCookieJar
    json_serialize: Callable[[Any], str]
    raise_for_status: bool
    timeout: ClientTimeout
    auto_decompress: bool
    read_bufsize: int
    trust_env: bool
    requote_redirect_url: bool
    trace_configs: list[TraceConfig] | None


RequestParams = tuple[Method, StrOrURL, SessionOpts]
