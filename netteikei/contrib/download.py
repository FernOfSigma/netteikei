import asyncio
from contextvars import ContextVar
from pathlib import Path
from typing import NamedTuple, Self, Unpack

import aiofiles
from aiohttp import ClientResponse, ClientSession
import tqdm

from .. import Client, Handler
from ..typedefs import Request, SessionOpts, StrOrURL
from .utils import isfile, parse_name, parse_length, get_start_byte


_DIR: ContextVar[Path] = ContextVar("dir")


class DownloadAlreadyExists(Exception):
    
    def __init__(self, path: Path) -> None:
        self.path = path

    def __str__(self) -> str:
        return f"'{self.path}' alredy exists"


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
            if await isfile(path) and start == length:
                raise DownloadAlreadyExists(path)
            return cls(url, path, length, start)


class Downloader(Handler[Download, None]):

    async def create_request(self) -> Request:
        dl = self.ctx.get()
        return Request.new(
            url=dl.url,
            headers={"Range": f"bytes={dl.start}-"}
        )

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
    limit: int = 3,
    **kwargs: Unpack[SessionOpts]
) -> None:
    token = _DIR.set(dir)
    async with ClientSession(**kwargs) as session:
        dls = await asyncio.gather(
            *(Download.new(session, url) for url in urls)
        )
        client = Client(session, Downloader(), max_workers=limit)
        await client.gather(*dls)
    _DIR.reset(token)
