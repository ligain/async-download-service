import asyncio

from aiohttp import web
import aiofiles
import datetime

CHUNK_SIZE = 120
CMD_TEMPLATE = 'zip -r - /home/linder/Documents/async-download-service/test_photos/{folder}/'

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


async def archivate(request):
    response = web.StreamResponse()

    cmd = CMD_TEMPLATE.format(folder='rur2')
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE
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


async def handle_index_page(request):
    async with aiofiles.open('index.html', mode='r') as index_file:
        index_contents = await index_file.read()
    return web.Response(text=index_contents, content_type='text/html')


if __name__ == '__main__':
    app = web.Application()
    app.add_routes([
        web.get('/', handle_index_page),
        web.get('/smoke', uptime_handler),
        web.get('/archive/{archive_hash}/', archivate),
    ])
    web.run_app(app)
