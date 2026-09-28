"""ASGI entry: `uvicorn qamra_api.main:app`."""

from qamra_api.app import create_app

app = create_app()
