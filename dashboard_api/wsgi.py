"""WSGI adapter for PythonAnywhere and other WSGI hosts.

This file exposes a WSGI `application` by adapting the FastAPI ASGI
app using `asgiref.wsgi.AsgiToWsgi`. Point your PythonAnywhere web app
to `dashboard_api.wsgi:application`.
"""
from __future__ import annotations

from asgiref.wsgi import AsgiToWsgi

from .app import app as asgi_app


application = AsgiToWsgi(asgi_app)
