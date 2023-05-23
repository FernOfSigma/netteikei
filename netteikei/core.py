from abc import ABC, abstractmethod
import asyncio
from collections.abc import Iterable
from contextvars import ContextVar
from typing import Generic, TypeVar, final

from aiohttp import ClientResponse, ClientSession

from .typedefs import Request


_T = TypeVar("_T")
_R = TypeVar("_R")


class Handler(ABC, Generic[_T, _R]):
    """Base class designed for making requests.

    Attributes
    ----------
    ctx
        Context variable possessing relevant data for making requests.
        The value is automatically set for each request.

    Methods
    -------
    create_request()
        Returns the request URL and options to override the options set
        in the underlying `aiohttp.ClientSession` instance. This method
        is called before making each request.
    process_response(resp)
        Processes the `aiohttp.ClientResponse` instance received as its
        only argument into relevant data. This method is called after a
        request has been made.
    """

    ctx: ContextVar[_T] = ContextVar("ctx")

    @abstractmethod
    async def create_request(self) -> Request:
        ...

    @abstractmethod
    async def process_response(self, res: ClientResponse) -> _R:
        ...


@final
class Client(Generic[_T, _R]):
    """
    Utility for making concurrent HTTP requests.

    Parameters
    ----------
    session
        An instance of `aiohttp.ClientSession`.
    handler
        Instance of a `Handler` implementation.
    max_workers, default 5
        Number of request workers that can run concurrently.

    See Also
    --------
    Handler : Abstract base class for making requests.
    """

    def __init__(
        self,
        session: ClientSession,
        handler: Handler[_T, _R],
        max_workers: int = 5
    ) -> None:
        self._session = session
        self._handler = handler
        self._sem = asyncio.Semaphore(max_workers)
    
    async def _request(self, obj: _T) -> _R:
        async with self._sem:
            self._handler.ctx.set(obj)
            method, url, opts = await self._handler.create_request()
            async with self._session.request(method, url, **opts) as res:
                return await self._handler.process_response(res)

    async def process(self, objs: Iterable[_T]) -> list[_R]:
        """Make multiple concurrent HTTP requests.

        Processes the given objects into relevant data using the provided
        `Handler` implementation.

        Parameters
        ----------
        objs
            Iterable containing data required for making requests.

        Returns
        -------
        list
            Results processed from the given data.
        """
        return await asyncio.gather(*(self._request(obj) for obj in objs))
