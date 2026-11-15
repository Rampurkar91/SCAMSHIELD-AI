"""Optional same-origin SPA hosting for the built production frontend."""
from pathlib import Path

from fastapi import FastAPI
from starlette.exceptions import HTTPException
from starlette.staticfiles import StaticFiles


class FrontendFiles(StaticFiles):
    async def get_response(self, path, scope):
        # Never turn missing API endpoints or private/dot files into HTML.
        parts = Path(path).parts
        if any(part.startswith('.') for part in parts) or (
            parts and parts[0] in {'api', 'health', 'docs', 'redoc', 'openapi.json'}
        ):
            raise HTTPException(404)
        try:
            return await super().get_response(path, scope)
        except HTTPException as error:
            headers = dict(scope.get('headers', []))
            accepts_html = b'text/html' in headers.get(b'accept', b'')
            if error.status_code != 404 or not accepts_html or Path(path).suffix:
                raise
            # Client-side routes need the SPA shell; missing assets must stay 404.
            return await super().get_response('index.html', scope)


def mount_frontend(app: FastAPI, directory):
    directory = Path(directory)
    if not (directory / 'index.html').is_file():
        raise RuntimeError('Frontend build missing. Build the root Dockerfile or run npm --prefix frontend run build.')
    # Called after API registration so real routes always win.
    app.mount('/', FrontendFiles(directory=directory, html=True), name='frontend')
