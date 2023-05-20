import asyncio
from contextvars import ContextVar
from pathlib import Path
from typing import NamedTuple, Self, Unpack

import aiofiles
from aiohttp import ClientResponse, ClientSession
import tqdm

from .. import Client, Handler, Request
from ..typedefs import SessionOpts, StrOrURL
from .utils import isfile, parse_name, parse_length, get_start_byte


_DIR: ContextVar[Path] = ContextVar("dir")


class DownloadAlreadyExists(Exception):
    
    def __init__(self, path: Path) -> None:
        self.path = path

    def __str__(self) -> str:
        return f"'{self.path}' alredy exists"


class DownloadInfo(NamedTuple):
    url: StrOrURL
    path: Path
    length: int | None
    start: int

    @classmethod
    async def find(cls, session: ClientSession, url: StrOrURL, /) -> Self:
        async with session.head(url, allow_redirects=True) as resp:
            name = parse_name(resp, "untitled")
            length = parse_length(resp.headers)
            path = _DIR.get() / name
            start = await get_start_byte(resp.headers, path)
            if await isfile(path) and start == length:
                raise DownloadAlreadyExists(path)
            return cls(url, path, length, start)


class DownloadHandler(Handler[DownloadInfo, None]):

    async def create_request(self) -> Request:
        info = self.ctx.get()
        return Request.new(
            url=info.url,
            headers={"Range": f"bytes={info.start}-"}
        )

    async def process_response(self, resp: ClientResponse) -> None:
        info = self.ctx.get()
        async with resp, aiofiles.open(info.path, "ab") as fp:
            with tqdm.tqdm(
                total=info.length,
                initial=info.start,
                unit="B",
                unit_scale=True,
                unit_divisor=1024
            ) as bar:
                async for chunk in resp.content.iter_any():
                    progress = await fp.write(chunk)
                    bar.update(progress)


async def download(
    dir: Path,
    /,
    *urls: StrOrURL,
    limit: int = 3,
    **kwargs: Unpack[SessionOpts]
) -> None:
    token = _DIR.set(dir)
    async with ClientSession(**kwargs) as session:
        info = await asyncio.gather(
            *(DownloadInfo.find(session, url) for url in urls)
        )
        client = Client(session, DownloadHandler(), max_workers=limit)
        await client.gather(*info)
    _DIR.reset(token)
