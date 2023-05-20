import asyncio
from collections.abc import Awaitable, Callable
import functools
import os
from pathlib import Path
from typing import ParamSpec, TypeVar

from aiohttp import ClientResponse
import pyrfc6266

from ..typedefs import Headers


_P = ParamSpec("_P")
_R = TypeVar("_R")


def wrap(fn: Callable[_P, _R]) -> Callable[_P, Awaitable[_R]]:
    @functools.wraps(fn)
    async def inner(*args: _P.args, **kwargs: _P.kwargs) -> _R:
        return await asyncio.to_thread(fn, *args, **kwargs)
    return inner


getsize = wrap(os.path.getsize)
isfile = wrap(os.path.isfile)


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
