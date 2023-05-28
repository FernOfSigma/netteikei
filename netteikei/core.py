import asyncio
from collections.abc import Iterable
from typing import Generic, final, overload

from aiohttp import ClientSession

from .typedefs import ReqHandler, ResHandler, T, U


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
    max_workers, default 5
        Number of request workers that can run concurrently.

    Methods
    -------
    run(session, objs, return_exceptions=False)
    """
    def __init__(
        self,
        *,
        handlers: tuple[ReqHandler[T], ResHandler[T, U]],
        max_workers: int = 5
    ) -> None:
        self._semaphore = asyncio.Semaphore(max_workers)
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
        return_exceptions: bool = False
    ) -> list[U]:
        ...

    @overload
    async def run(
        self,
        session: ClientSession,
        objs: Iterable[T],
        /,
        return_exceptions: bool = True
    ) -> list[U | BaseException]:
        ...

    async def run(
        self,
        session: ClientSession,
        objs: Iterable[T],
        /,
        return_exceptions: bool = False
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
