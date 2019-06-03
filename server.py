import asyncio
import os
import datetime

import aiofiles
from aiohttp import web
from aiohttp.web_exceptions import HTTPNotFound


CHUNK_SIZE = 120
BASE_PHOTOS_PATH = 'test_photos/'
CMD = 'zip - *'
INTERVAL_SECS = 1


async def uptime_handler(request):
    response = web.StreamResponse()
    response.headers['Content-Type'] = 'text/html'
    await response.prepare(request)

    while True:
        formatted_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f'{formatted_date}<br>'
        await response.write(message.encode('utf-8'))
        await asyncio.sleep(INTERVAL_SECS)


async def archive_handler(request):
    archive_hash = request.match_info['archive_hash']
    response = web.StreamResponse()

    photos_path = os.path.abspath(os.path.join(BASE_PHOTOS_PATH, archive_hash))
    if not os.path.exists(photos_path):
        raise HTTPNotFound

    proc = await asyncio.create_subprocess_shell(
        CMD,
        stdout=asyncio.subprocess.PIPE,
        cwd=photos_path
    )

    response.headers['Content-Disposition'] = 'attachment; filename="archive.zip"'
    await response.prepare(request)

    while True:
        archive_chunk = await proc.stdout.read(CHUNK_SIZE)
        await response.write(archive_chunk)
        if not archive_chunk:
            break
    await proc.wait()

    await response.write_eof()
    return response


async def index_page_handler(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


if __name__ == '__main__':
    app = web.Application()
    app.add_routes([
        web.get('/', index_page_handler),
        web.get('/uptime', uptime_handler),
        web.get('/archive/{archive_hash}/', archive_handler),
    ])
    web.run_app(app)
