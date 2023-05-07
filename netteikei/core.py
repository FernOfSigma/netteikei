from abc import ABC, abstractmethod
import asyncio
from contextvars import ContextVar
from typing import Generic, TypeVar, final

from aiohttp import ClientResponse, ClientSession

from .typedefs import RequestParams


T = TypeVar("T")
U = TypeVar("U")


class RequestHandler(ABC, Generic[T, U]):
    """
    Base class designed as a template for making concurrent HTTP requests.

    Attributes
    ----------
    ctx
        Context variable possessing relevant data for making requests.
        Its value is set automatically for each request.

    Methods
    -------
    generate_params()
        Returns the HTTP method, URL and options for the request.
        These options override the options set in the underlying
        `aiohttp.ClientSession` instance. This method is automatically
        called before making each request.

    process_response(resp)
        Processes the `aiohttp.ClientResponse` instance received as its
        only argument into the relevant result. This method is called
        automatically after a request has been made.
    """

    ctx: ContextVar[T] = ContextVar("ctx")

    @abstractmethod
    async def generate_params(self) -> RequestParams:
        ...

    @abstractmethod
    async def process_response(self, resp: ClientResponse) -> U:
        ...


@final
class Client(Generic[T, U]):
    """
    Utility for making concurrent HTTP requests.

    Parameters
    ----------
    session
        An instance of `aiohttp.ClientSession`.
    handler
        Instance of a `RequestHandler` implementation.
    max_workers, default 5
        Number of request workers that can run concurrently.

    See Also
    --------
    netteikei.RequestHandler : Abstract base class for making requests.
    """

    def __init__(
        self,
        session: ClientSession,
        handler: RequestHandler[T, U],
        max_workers: int = 5
    ) -> None:
        self._session = session
        self._handler = handler
        self._sem = asyncio.Semaphore(max_workers)
    
    async def _request(self, obj: T) -> U:
        async with self._sem:
            self._handler.ctx.set(obj)
            method, url, opts = await self._handler.generate_params()
            async with self._session.request(method, url, **opts) as resp:
                return await self._handler.process_response(resp)

    async def gather(self, *args: T) -> list[U]:
        """
        Processes data into relevant results using the `RequestHandler`
        implementation provided by the user.

        Parameters
        ----------
        *args
            Data required for making requests.

        Returns
        -------
        list
            Results processed from the given data.
        """
        return await asyncio.gather(*(self._request(obj) for obj in args))
