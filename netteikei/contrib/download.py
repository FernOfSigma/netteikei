import asyncio
from contextvars import ContextVar
from pathlib import Path
from typing import NamedTuple, Self, Unpack

import aiofiles
from aiohttp import ClientResponse, ClientSession
from aiohttp.typedefs import LooseHeaders, StrOrURL
import pyrfc6266
import tqdm

from .. import Client, Request
from ..typedefs import SessionKwargs
from .utils import getsize, isfile


download_dir: ContextVar[Path] = ContextVar("dir")


class DuplicateDownloadError(Exception):
    
    def __init__(self, path: Path) -> None:
        self.path = path

    def __str__(self) -> str:
        return f"Download has already been saved in {self.path}."

        
def _parse_name(res: ClientResponse, default: str) -> str:
    if (s := res.headers.get("Content-Disposition")) is None:
        return res.url.name
    else:
        if (name := pyrfc6266.parse_filename(s)) is None:
            return default
        return name


def _parse_length(headers: LooseHeaders) -> int | None:
    if (s := headers.get("Content-Length")) is not None:
        return int(s)
    return


async def _get_start_offset(headers: LooseHeaders, file: Path) -> int:
    if headers.get("Accept-Ranges") == "bytes" and await isfile(file):
        return await getsize(file)
    return 0


class Properties(NamedTuple):
    url: StrOrURL
    path: Path
    length: int | None
    offset: int

    @classmethod
    async def fetch(cls, session: ClientSession, url: StrOrURL) -> Self:
        async with session.head(url, allow_redirects=True) as res:
            name = _parse_name(res, "untitled")
            length = _parse_length(res.headers)
            path = download_dir.get() / name
            offset = await _get_start_offset(res.headers, path)

            # Throw an error if the file already exists and isn't empty.
            if await isfile(path) and 0 < offset == length:
                raise DuplicateDownloadError(path)

            return cls(url, path, length, offset)


async def handle_req(prop: Properties) -> Request:
    # Do not send redundant headers when starting a new download.
    headers = {} if prop.offset == 0 else {"Range": f"bytes={prop.offset}-"}
    return Request.new(url=prop.url, headers=headers)

async def handle_res(prop: Properties, res: ClientResponse) -> None:
    async with res, aiofiles.open(prop.path, "ab") as fp:
        with tqdm.tqdm(
            total=prop.length,
            initial=prop.offset,
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
    **kwargs: Unpack[SessionKwargs]
) -> None:
    """Asynchronously download files.

    Parameters
    ----------
    dir
        Directory where downloads will be stored.
    *urls
        URLs to download from.
    **opts
        Init options for the underlying `aiohttp.ClientSession`.

    Raises
    ------
    DuplicateDownloadError
        Raised when the file has already been downloaded.
    """
    token = download_dir.set(dir)
    async with ClientSession(**kwargs) as session:
        props: list[Properties] = await asyncio.gather(
            *(Properties.fetch(session, url) for url in urls)
        )
        client = Client(handlers=(handle_req, handle_res), limit=limit)
        await client.run(session, props, return_exceptions=True)
    download_dir.reset(token)
