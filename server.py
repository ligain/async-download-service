import asyncio
import os
import datetime
import logging

import aiofiles
from aiohttp import web
from aiohttp.web_exceptions import HTTPNotFound

from middlewares import error_middleware


CHUNK_SIZE = 2048
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
    archive_process = await asyncio.create_subprocess_shell(
        CMD,
        stdout=asyncio.subprocess.PIPE,
        cwd=photos_path
    )

    response.headers['Content-Disposition'] = 'attachment; filename="archive.zip"'
    await response.prepare(request)

    try:
        while True:
            archive_chunk = await archive_process.stdout.read(CHUNK_SIZE)
            logging.debug('Sending archive chunk ...')
            await response.write(archive_chunk)
            if not archive_chunk:
                break
            # await asyncio.sleep(5)
    except asyncio.CancelledError:
        logging.debug('Download was interrupted')
        archive_process.terminate()
        await archive_process.wait()
        logging.debug(f'Archive process with PID: {archive_process.pid} was stopped. '
                      f'Return code: {archive_process.returncode}')

        raise
    finally:
        await archive_process.wait()
        response.force_close()
    return response


async def index_page_handler(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG,
                        format='[%(asctime)s] %(funcName)s: %(levelname).1s %(message)s',
                        datefmt='%Y.%m.%d %H:%M:%S')
    app = web.Application(middlewares=[error_middleware])
    app.add_routes([
        web.get('/', index_page_handler),
        web.get('/uptime', uptime_handler),
        web.get('/archive/{archive_hash}/', archive_handler),
    ])
    web.run_app(app)
