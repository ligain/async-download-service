import asyncio
import os
import datetime
import logging
import argparse

import aiofiles
from aiohttp import web
from aiohttp.web_exceptions import HTTPNotFound
from functools import partial

from middlewares import error_middleware


async def uptime_handler(request, interval_sec=1):
    response = web.StreamResponse()
    response.headers['Content-Type'] = 'text/html'
    await response.prepare(request)

    while True:
        formatted_date = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f'{formatted_date}<br>'
        await response.write(message.encode('utf-8'))
        await asyncio.sleep(interval_sec)


async def archive_handler(request, delay=None, base_photos_path=None, chunk_size=2048):
    archive_hash = request.match_info['archive_hash']
    response = web.StreamResponse()

    photos_path = os.path.abspath(os.path.join(base_photos_path, archive_hash))
    if not os.path.exists(photos_path):
        raise HTTPNotFound
    archive_process = await asyncio.create_subprocess_exec(
        'zip', '-jr', '-', photos_path,
        stdout=asyncio.subprocess.PIPE
    )

    response.headers['Content-Disposition'] = 'attachment; filename="archive.zip"'
    await response.prepare(request)

    try:
        while True:
            archive_chunk = await archive_process.stdout.read(chunk_size)
            logging.debug('Sending archive chunk ...')
            await response.write(archive_chunk)
            if not archive_chunk:
                break
            if delay:
                await asyncio.sleep(delay)
    except asyncio.CancelledError:
        logging.debug('Download was interrupted')
        archive_process.kill()
        await archive_process.wait()
        logging.debug(f'Archive process with PID: {archive_process.pid} was stopped. '
                      f'Return code: {archive_process.returncode}')
        raise
    finally:
        response.force_close()

    return response


async def index_page_handler(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


def get_args():
    parser = argparse.ArgumentParser(
        description='Microservice to download photo archives'
    )
    parser.add_argument(
        '-l', '--log',
        help='Turn on logging',
        action='store_true',
        default=os.getenv('LOG')
    )
    parser.add_argument(
        '-d', '--delay',
        help='Response delay in sec',
        type=float,
        default=os.getenv('DELAY')
    )
    parser.add_argument(
        '-p', '--photos-path',
        help='Base path to photos directory',
        default=os.getenv('BASE_PHOTOS_PATH', 'test_photos/'),
        dest='base_photos_path'
    )
    return parser.parse_args()


if __name__ == '__main__':
    args = get_args()
    if args.log:
        logging.basicConfig(level=logging.DEBUG,
                            format='[%(asctime)s] %(funcName)s: %(levelname).1s %(message)s',
                            datefmt='%Y.%m.%d %H:%M:%S')
    app = web.Application(middlewares=[error_middleware])
    app.add_routes([
        web.get('/', index_page_handler),
        web.get('/uptime', uptime_handler),
        web.get('/archive/{archive_hash}/', partial(
            archive_handler,
            delay=args.delay,
            base_photos_path=args.base_photos_path
        )),
    ])
    web.run_app(app)
