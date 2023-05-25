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


__all__ = ["download"]

DOWNLOAD_DIR: ContextVar[Path] = ContextVar("dir")


class DownloadAlreadyExists(Exception):
    
    def __init__(self, path: Path) -> None:
        self.path = path

    def __str__(self) -> str:
        return f"Download has already been saved in {self.path}."


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
            path = DOWNLOAD_DIR.get() / name
            start = await get_start_byte(resp.headers, path)

            # Throw an error if the file already exists and isn't empty.
            if await isfile(path) and 0 < start == length:
                raise DownloadAlreadyExists(path)

            return cls(url, path, length, start)


class DownloadHandler(Handler[DownloadInfo, None]):

    async def create_request(self) -> Request:
        info = self.ctx.get()
        # Don't send extra headers when starting a download from the beginning
        # of a file.
        headers = {} if info.start == 0 else {"Range": f"bytes={info.start}-"} 
        return Request.new(url=info.url, headers=headers)

    async def process_response(self, res: ClientResponse) -> None:
        info = self.ctx.get()
        async with res, aiofiles.open(info.path, "ab") as fp:
            with tqdm.tqdm(
                total=info.length,
                initial=info.start,
                unit="B",
                unit_scale=True,
                unit_divisor=1024
            ) as bar:
                async for chunk in res.content.iter_any():
                    progress = await fp.write(chunk)
                    bar.update(progress)


async def download(
    dir: Path,
    /,
    *urls: StrOrURL,
    limit: int = 3,
    **opts: Unpack[SessionOpts]
) -> None:
    """Asynchronously download files.

    Parameters
    ----------
    dir
        Directory where downloads will be stored.
    *urls
        URLs to download from.
    **opts
        Initialization options for the underlying `aiohttp.ClientSession`.

    Raises
    ------
    DownloadAlreadyExists
        Raised when the file has already been downloaded.
    """
    token = DOWNLOAD_DIR.set(dir)
    async with ClientSession(**opts) as session:
        info = await asyncio.gather(
            *(DownloadInfo.find(session, url) for url in urls)
        )
        client = Client(session, DownloadHandler(), max_workers=limit)
        await client.process(info)
    DOWNLOAD_DIR.reset(token)
