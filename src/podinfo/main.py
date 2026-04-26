from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, Query, Request
from fastapi.templating import Jinja2Templates

from .logic import PodInfo, safe_css_background

app = FastAPI(
    title="podinfo", version=os.getenv("APP_VERSION", "unknown")
)
pod_info = PodInfo()

templates = Jinja2Templates(
    directory=str(Path(__file__).resolve().parent / "templates")
)
templates.env.filters["safe_css_bg"] = safe_css_background


@app.get("/")
def root(request: Request):
    ctx = pod_info.get_dashboard_html()
    return templates.TemplateResponse(
        request, "dashboard.html", ctx
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/version")
def version() -> dict[str, str]:
    return pod_info.get_version()


@app.get("/info")
def info() -> dict[str, str]:
    return pod_info.get_info()


@app.get("/echo")
def echo(message: str = Query(...)) -> dict[str, object]:
    return pod_info.echo_message(message)


def main():
    import uvicorn

    uvicorn.run(
        "podinfo.main:app",
        host="0.0.0.0",
        port=8080,
    )


if __name__ == "__main__":
    main()
