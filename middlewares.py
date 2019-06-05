from aiohttp import web
from http import HTTPStatus


@web.middleware
async def error_middleware(request, handler):
    try:
        response = await handler(request)
        if response.status != HTTPStatus.NOT_FOUND:
            return response
    except web.HTTPException as ex:
        if ex.status != HTTPStatus.NOT_FOUND:
            raise
    return web.Response(text='Archive was not found or removed')
