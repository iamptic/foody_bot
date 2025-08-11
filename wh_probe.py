# wh_probe.py — минимальная проверка роутинга
from aiohttp import web
import os
app = web.Application()
app.router.add_get('/',        lambda r: web.Response(text='OK'))
app.router.add_get('/tg/webhook', lambda r: web.Response(text='OK'))
app.router.add_post('/tg/webhook', lambda r: web.Response(text='OK'))
web.run_app(app, host='0.0.0.0', port=int(os.getenv('PORT','8000')))
