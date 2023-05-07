import asyncio
from contextvars import ContextVar
from pathlib import Path
from typing import NamedTuple, Self, Unpack

import aiofiles
from aiohttp import ClientResponse, ClientSession
import tqdm

from .. import Client, RequestHandler
from ..typedefs import (
    RequestParams,
    SessionOpts,
    StrOrURL
)
from .utils import (
    parse_name,
    parse_length,
    get_start_byte
)


_DIR: ContextVar[Path] = ContextVar("dir")


class DownloadAlreadyExists(Exception):
    
    def __init__(self, name: str) -> None:
        self.name = name

    def __str__(self) -> str:
        return f"'{self.name}' alredy exists"


class Download(NamedTuple):
    url: StrOrURL
    path: Path
    length: int | None
    start: int

    @classmethod
    async def new(cls, session: ClientSession, url: StrOrURL, /) -> Self:
        async with session.head(url) as resp:
            name = parse_name(resp, "untitled")
            length = parse_length(resp.headers)
            path = _DIR.get() / name
            start = await get_start_byte(resp.headers, path)
            if start == length:
                raise DownloadAlreadyExists(name)
            return cls(url, path, length, start)


class DownloadHandler(RequestHandler[Download, None]):

    async def generate_params(self) -> RequestParams:
        dl = self.ctx.get()
        return "GET", dl.url, {"headers": {"Range": f"bytes={dl.start}-"}}

    async def process_response(self, resp: ClientResponse) -> None:
        dl = self.ctx.get()
        async with resp, aiofiles.open(dl.path, "wb") as f:
            with tqdm.tqdm(
                total=dl.length,
                initial=dl.start,
                unit="B",
                unit_scale=True,
                unit_divisor=1024
            ) as pbar:
                if dl.start != 0:
                    await f.seek(dl.start)
                async for chunk in resp.content.iter_any():
                    await f.write(chunk)
                    pbar.update(len(chunk))


async def download(
    dir: Path,
    /,
    *urls: StrOrURL,
    concurrent_limit: int = 3,
    **kwargs: Unpack[SessionOpts]
) -> None:
    _DIR.set(dir)
    async with ClientSession(**kwargs) as session:
        dls = await asyncio.gather(
            *(Download.new(session, url) for url in urls)
        )
        client = Client(
            session=session,
            handler=DownloadHandler(),
            max_workers=concurrent_limit
        )
        await client.gather(*dls)
