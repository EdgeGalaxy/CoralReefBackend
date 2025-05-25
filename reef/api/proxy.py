from fastapi import APIRouter, Request, Response
from typing import Dict, Any
from fastapi.responses import RedirectResponse

from reef.core.proxy import ProxyCore


router = APIRouter(prefix="/proxy", tags=["proxy"])


@router.post("/")
async def proxy_request_post(url: str, request: Request):
    data = await request.json()
    proxy_core = ProxyCore(url=url, method="POST")
    return await proxy_core.dispatch(data)


@router.get("/")
async def proxy_request_get(url: str):
    proxy_core = ProxyCore(url=url, method="GET")
    return await proxy_core.dispatch(data={})