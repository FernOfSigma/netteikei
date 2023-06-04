import asyncio
from collections.abc import Iterable
from typing import Generic, Literal, final, overload

from aiohttp import ClientSession

from .typedefs import RequestHandler, ResponseHandler, T, U


@final
class Client(Generic[T, U]):
    """Utility for making concurrent HTTP requests.

    Parameters
    ----------
    session
        An instance of `aiohttp.ClientSession`.
    handlers
        Tuple containing the request and response handler pair.

        The request handler returns the request method, URL, and options
        that override the options set within the `aiohttp.ClientSession`
        used underneath.

        The response handler receieves a `aiohttp.ClientResponse` as its
        second argument which is processed into relevant data.

        Both handlers are asynchronous, and are called before and after
        each request made respectively.
    limit, default 10
        Number of requests that can run concurrently.

    Methods
    -------
    run(session, objs, return_exceptions=False)
    """
    def __init__(
        self,
        *,
        handlers: tuple[RequestHandler[T], ResponseHandler[T, U]],
        limit: int = 10
    ) -> None:
        self._semaphore = asyncio.Semaphore(limit)
        self._req_handler, self._res_handler = handlers
    
    async def _request(self, session: ClientSession, obj: T) -> U:
        async with self._semaphore:
            method, url, kwargs = await self._req_handler(obj)
            async with session.request(method, url, **kwargs) as res:
                return await self._res_handler(obj, res)

    @overload
    async def run(
        self,
        session: ClientSession,
        objs: Iterable[T],
        /,
        return_exceptions: Literal[False] = False
    ) -> list[U]:
        ...

    @overload
    async def run(
        self,
        session: ClientSession,
        objs: Iterable[T],
        /,
        return_exceptions: Literal[True]
    ) -> list[U | BaseException]:
        ...

    async def run(
        self,
        session: ClientSession,
        objs: Iterable[T],
        /,
        return_exceptions: Literal[True, False] = False
    ) -> list[U] | list[U | BaseException]:
        """Make concurrent HTTP requests.

        Processes the given objects into relevant data using the user
        provided handlers.

        Parameters
        ----------
        session
            An instance of `aiohttp.ClientSession`.
        objs
            Iterable containing data required for making requests.
        return_exceptions, default False
            When this is `True`, exceptions are treated as successful
            results and are returned along with the processed data.

        Returns
        -------
        list
            Results processed from the given data.
        """
        return await asyncio.gather(
            *(self._request(session, obj) for obj in objs),
            return_exceptions=return_exceptions
        )
