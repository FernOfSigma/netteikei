import asyncio
from collections.abc import Awaitable, Callable
import functools
import os
from pathlib import Path
from typing import ParamSpec, TypeVar

from aiohttp import ClientResponse
import pyrfc6266

from ..typedefs import Headers

P = ParamSpec("P")
T = TypeVar("T")

def _wrap(fn: Callable[P, T]) -> Callable[P, Awaitable[T]]:
    @functools.wraps(fn)
    async def inner(*args: P.args, **kwargs: P.kwargs) -> T:
        return await asyncio.to_thread(fn, *args, **kwargs)
    return inner

getsize = _wrap(os.path.getsize)
isfile = _wrap(os.path.isfile)

def parse_name(resp: ClientResponse, default: str) -> str:
    if (s := resp.headers.get("Content-Disposition")) is None:
        return resp.url.name
    else:
        if (name := pyrfc6266.parse_filename(s)) is None:
            return default
        return name

def parse_length(headers: Headers) -> int | None:
    if (s := headers.get("Content-Length")) is not None:
        return int(s)

async def get_start_byte(headers: Headers, file: Path) -> int:
    if headers.get("Accept-Ranges") == "bytes" and await isfile(file):
        return await getsize(file)
    return 0
