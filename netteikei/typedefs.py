from collections.abc import Awaitable, Callable, Iterable, Mapping
from typing import (
    Any,
    Literal,
    NamedTuple,
    Self,
    TypeVar,
    TypedDict,
    Unpack
)

from aiohttp import (
    BaseConnector,
    BasicAuth,
    ClientResponse,
    ClientTimeout,
    HttpVersion,
    TraceConfig
)
from aiohttp.abc import AbstractCookieJar
from aiohttp.typedefs import StrOrURL
from multidict import istr


Method = Literal["POST", "GET", "PUT", "HEAD", "PATCH", "OPTIONS", "DELETE"]
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


class Opts(SessionOpts, total=False):
    allow_redirects: bool
    data: Any


class Request(NamedTuple):
    method: Method
    url: StrOrURL
    opts: Opts

    @classmethod
    def new(
        cls,
        *,
        method: Method = "GET",
        url: StrOrURL,
        **opts: Unpack[Opts]
    ) -> Self:
        return cls(method, url, opts)


T, U = TypeVar("T"), TypeVar("U")

ReqHandler = Callable[[T], Awaitable[Request]]
ResHandler = Callable[[T, ClientResponse], Awaitable[U]]
