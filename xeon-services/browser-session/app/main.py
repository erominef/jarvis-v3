# main.py — Stateful browser session service.
#
# Runs on Xeon in Docker at port 8086.
# Manages Playwright browser sessions for multi-step web automation.
# Sessions auto-expire after 10 minutes of inactivity. Max 5 concurrent.
#
# Endpoints:
#   POST   /open       {url}                     -> {session_id, title, url}
#   GET    /state      ?session_id=              -> {url, title, elements: [{ref, tag, text, type}]}
#   POST   /click      {session_id, ref}         -> {success, url}
#   POST   /type       {session_id, ref, text}   -> {success}
#   POST   /navigate   {session_id, url}         -> {success, title, url}
#   POST   /close      {session_id}              -> {success}

import asyncio
import secrets
import time

from fastapi import FastAPI
from pydantic import BaseModel
from playwright.async_api import async_playwright

app = FastAPI(title="jarvis-browser-session")

_SELECTOR = "a, button, input:not([type='hidden']), textarea, select, [role='button'], [role='link']"
_MAX_SESSIONS = 5
_SESSION_TTL = 600  # 10 minutes

_pw = None
_browser = None
_sessions: dict = {}  # {session_id: {"page": Page, "last_used": float}}


@app.on_event("startup")
async def startup():
    global _pw, _browser
    _pw = await async_playwright().start()
    _browser = await _pw.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
    )
    asyncio.create_task(_cleanup_loop())


@app.on_event("shutdown")
async def shutdown():
    for s in _sessions.values():
        try:
            await s["page"].context.close()
        except Exception:
            pass
    if _browser:
        await _browser.close()
    if _pw:
        await _pw.stop()


async def _cleanup_loop():
    while True:
        await asyncio.sleep(60)
        now = time.time()
        expired = [sid for sid, s in list(_sessions.items()) if now - s["last_used"] > _SESSION_TTL]
        for sid in expired:
            try:
                await _sessions[sid]["page"].context.close()
            except Exception:
                pass
            _sessions.pop(sid, None)


def _touch(session_id: str):
    if session_id in _sessions:
        _sessions[session_id]["last_used"] = time.time()


async def _elements(page) -> list:
    els = await page.query_selector_all(_SELECTOR)
    result = []
    for i, el in enumerate(els[:50]):
        try:
            tag = await el.evaluate("el => el.tagName.toLowerCase()")
            text = (await el.inner_text()).strip()[:100]
            el_type = await el.get_attribute("type") or ""
            result.append({"ref": i, "tag": tag, "text": text or tag, "type": el_type})
        except Exception:
            result.append({"ref": i, "tag": "?", "text": "", "type": ""})
    return result


class OpenReq(BaseModel):
    url: str

class ClickReq(BaseModel):
    session_id: str
    ref: int

class TypeReq(BaseModel):
    session_id: str
    ref: int
    text: str

class NavReq(BaseModel):
    session_id: str
    url: str

class CloseReq(BaseModel):
    session_id: str


@app.post("/open")
async def open_session(req: OpenReq):
    if len(_sessions) >= _MAX_SESSIONS:
        return {"success": False, "error": "max_sessions_reached"}
    try:
        ctx = await _browser.new_context()
        page = await ctx.new_page()
        await page.goto(req.url, timeout=30000)
        sid = secrets.token_hex(4)
        _sessions[sid] = {"page": page, "last_used": time.time()}
        return {"success": True, "session_id": sid, "title": await page.title(), "url": page.url}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/state")
async def get_state(session_id: str):
    s = _sessions.get(session_id)
    if not s:
        return {"success": False, "error": "session_not_found"}
    _touch(session_id)
    try:
        page = s["page"]
        return {"success": True, "url": page.url, "title": await page.title(), "elements": await _elements(page)}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/click")
async def click_element(req: ClickReq):
    s = _sessions.get(req.session_id)
    if not s:
        return {"success": False, "error": "session_not_found"}
    _touch(req.session_id)
    try:
        page = s["page"]
        els = await page.query_selector_all(_SELECTOR)
        if req.ref >= len(els):
            return {"success": False, "error": "ref_out_of_range"}
        await els[req.ref].click()
        try:
            await page.wait_for_load_state("load", timeout=5000)
        except Exception:
            pass  # click didn't trigger navigation — that's fine
        return {"success": True, "url": page.url}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/type")
async def type_text(req: TypeReq):
    s = _sessions.get(req.session_id)
    if not s:
        return {"success": False, "error": "session_not_found"}
    _touch(req.session_id)
    try:
        page = s["page"]
        els = await page.query_selector_all(_SELECTOR)
        if req.ref >= len(els):
            return {"success": False, "error": "ref_out_of_range"}
        await els[req.ref].fill(req.text)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/navigate")
async def navigate(req: NavReq):
    s = _sessions.get(req.session_id)
    if not s:
        return {"success": False, "error": "session_not_found"}
    _touch(req.session_id)
    try:
        page = s["page"]
        await page.goto(req.url, timeout=30000)
        return {"success": True, "title": await page.title(), "url": page.url}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/close")
async def close_session(req: CloseReq):
    s = _sessions.pop(req.session_id, None)
    if not s:
        return {"success": False, "error": "session_not_found"}
    try:
        await s["page"].context.close()
    except Exception:
        pass
    return {"success": True}
