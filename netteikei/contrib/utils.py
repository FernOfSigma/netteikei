import asyncio
from collections.abc import Awaitable, Callable
import functools
import os
from typing import ParamSpec, TypeVar


P = ParamSpec("P")
T = TypeVar("T")


def wrap(fn: Callable[P, T]) -> Callable[P, Awaitable[T]]:
    @functools.wraps(fn)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        return await asyncio.to_thread(fn, *args, **kwargs)
    return wrapper


getsize = wrap(os.path.getsize)
isfile = wrap(os.path.isfile)
makedirs = wrap(os.makedirs)
