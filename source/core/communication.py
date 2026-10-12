from __future__ import annotations

import threading
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.verchain import Verchain


class VerchainAPI:
    """Builds and serves the HTTP API for a Verchain node."""

    def __init__(self, verchain: Verchain) -> None:
        self.verchain = verchain

    def startAPI(self) -> None:
        app = self.buildAPI()
        thread = threading.Thread(
            target=uvicorn.run,
            args=(app,),
            kwargs={
                "host": self.verchain.host,
                "port": self.verchain.port + 10000,
                "log_level": "warning",
            },
            daemon=True,
        )
        thread.start()

    def buildAPI(self) -> FastAPI:
        from API.router import VerchainRouter

        app = FastAPI(title=f"Verchain - {self.verchain.title}")
        apiPort = self.verchain.port + 10000
        apiOrigin = f"http://{self.verchain.host}:{apiPort}"
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[
                apiOrigin,
                f"http://localhost:{apiPort}",
                f"http://127.0.0.1:{apiPort}",
                "*",
            ],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        app.include_router(VerchainRouter(self.verchain.processor))
        staticDir = Path(__file__).resolve().parents[1] / "API" / "static"
        app.mount("/console", StaticFiles(directory=staticDir, html=True), name="Console")
        return app
