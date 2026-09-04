# TICKET-332 — content_api module docstring over-promises "compatible with any WSGI/ASGI framework"

- Status: RESOLVED
- Class: (b) doc/behavior drift
- Module: personal_index/content_api.py
- Issue: #502

## Symptom
The `content_api` module docstring (lines 1-5) claims the module "Uses a
lightweight approach compatible with any WSGI/ASGI framework." No such
compatibility exists anywhere in the module: `ContentAPI.handle_request`
exposes a custom interface
`handle_request(method, path, body, query_string) -> tuple[int, dict]`, and
the `LoggingMiddleware` wraps the same custom interface. There is no WSGI
`__call__(self, environ, start_response)` method and no ASGI
`__call__(self, scope, receive, send)` method, so the module is not directly
pluggable into any WSGI/ASGI framework. The "compatible with any WSGI/ASGI
framework" capability is an over-promise.

## Evidence
- `sed -n '1,5p' personal_index/content_api.py` shows the module docstring
  ending with "Uses a lightweight approach compatible with any WSGI/ASGI
  framework."
- `grep -n 'environ\|start_response\|scope\|receive\|send\|__call__\|wsgi\|asgi\|WSGI\|ASGI'
  personal_index/content_api.py` matches ONLY line 4 (the docstring itself);
  no WSGI/ASGI interface symbol is defined anywhere in the module.
- `ContentAPI.handle_request` (lines 23-35) takes
  `(method, path, body, query_string)` and returns `(int, dict)` — a custom
  request/response shape, not the WSGI `environ`/`start_response` contract nor
  the ASGI `scope`/`receive`/`send` contract.
- `LoggingMiddleware.handle_request` (lines 206-216) delegates to the same
  custom `api.handle_request(method, path, body, query_string)` interface.

## Minimal additive fix
Correct the module docstring to describe only the interface actually
implemented. Change line 4 from
"Uses a lightweight approach compatible with any WSGI/ASGI framework." to
"Exposes a lightweight request/response interface
(`handle_request(method, path, body, query_string) -> (status, payload)`)
that callers can adapt to their own HTTP framework." (the real behavior: a
framework-agnostic request handler, not a WSGI/ASGI adapter).

Add ONE regression test
`TestContentApiDocstring::test_docstring_does_not_promise_wsgi_asgi_compatibility`
that asserts "WSGI" and "ASGI" are absent from the `content_api` module
`__doc__`, so the over-promise cannot silently return.
