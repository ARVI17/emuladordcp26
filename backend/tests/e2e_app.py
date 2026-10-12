"""Disposable browser harness. Production starts app.main, never this module."""
import json
import os
from catalog_fixture import activate_seed, prepare_payload, safe_database
from app.db.seed import seed_database
from app.db.bootstrap import bootstrap
from app.main import app as application

if os.environ.get('PLAYWRIGHT_DISPOSABLE_DB') != '1':
    raise RuntimeError('Browser fixtures require explicit disposable mode')
safe_database()
seed_database()
activate_seed()
bootstrap()


class FixtureEvidence:
    def __init__(self, wrapped):
        self.wrapped = wrapped

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or dict(scope['headers']).get(b'x-catalog-fixture') != b'1' or scope['method'] not in {'POST', 'PATCH'}:
            return await self.wrapped(scope, receive, send)
        chunks = []
        more = True
        while more:
            message = await receive()
            chunks.append(message.get('body', b''))
            more = message.get('more_body', False)
        data = b''.join(chunks)
        try:
            value = json.loads(data)
        except ValueError:
            value = None
        if value is not None:
            data = json.dumps(prepare_payload(scope['path'], scope['method'], value)).encode()
        sent = False
        async def replay():
            nonlocal sent
            if not sent:
                sent = True
                return {'type': 'http.request', 'body': data, 'more_body': False}
            return await receive()
        await self.wrapped(scope, replay, send)


app = FixtureEvidence(application)
