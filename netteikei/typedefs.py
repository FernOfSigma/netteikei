from collections.abc import Awaitable, Callable, Iterable, Mapping
from types import SimpleNamespace
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
    Fingerprint,
    HttpVersion,
    TraceConfig
)
from aiohttp.connector import SSLContext
from aiohttp.abc import AbstractCookieJar
from aiohttp.typedefs import (
    JSONEncoder, 
    StrOrURL,
    LooseHeaders,
    LooseCookies
)


Method = Literal["POST", "GET", "PUT", "HEAD", "PATCH", "OPTIONS", "DELETE"]


# Wide type hints according to the aiohttp 3.8.4 documentation.
class SessionKwargs(TypedDict, total=False):
    base_url: StrOrURL
    connector: BaseConnector
    cookies: LooseCookies
    headers: LooseHeaders
    skip_auto_headers: Iterable[str]
    auth: BasicAuth
    json_serialize: JSONEncoder
    version: HttpVersion
    cookie_jar: AbstractCookieJar
    connector_owner: bool
    raise_for_status: bool
    timeout: ClientTimeout
    auto_decompress: bool
    read_bufsize: int
    trust_env: bool
    requote_redirect_url: bool
    trace_configs: list[TraceConfig] | None


class RequestKwargs(TypedDict, total=False):
    params: Mapping[str, str]
    data: Any
    json: Any
    headers: LooseHeaders
    skip_auto_headers: Iterable[str]
    auth: BasicAuth
    allow_redirects: bool
    max_redirects: int
    compress: bool
    # Docs are ambiguious for this keyword.
    # chunked: bool
    expect100: bool
    raise_for_status: bool
    read_until_eof: bool
    read_bufsize: int
    proxy: StrOrURL
    proxy_auth: BasicAuth
    timeout: ClientTimeout
    ssl: SSLContext | bool | Fingerprint
    proxy_headers: LooseHeaders
    trace_request_ctx: SimpleNamespace


class Request(NamedTuple):
    method: Method
    url: StrOrURL
    kwargs: RequestKwargs

    @classmethod
    def new(
        cls,
        *,
        method: Method = "GET",
        url: StrOrURL,
        **kwargs: Unpack[RequestKwargs]
    ) -> Self:
        return cls(method, url, kwargs)


T, U = TypeVar("T"), TypeVar("U")

ReqHandler = Callable[[T], Awaitable[Request]]
ResHandler = Callable[[T, ClientResponse], Awaitable[U]]
