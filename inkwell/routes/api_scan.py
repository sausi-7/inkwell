"""Scan trigger + SSE progress stream, with single-scan guard and cancel.

- `POST /api/scan` → start a scan. Returns 409 if one is already running.
- `GET  /api/scan/status` → `{running, started_at, current_subreddit}`.
- `POST /api/scan/stop` → sets cancel flag; worker exits between subreddits.

The worker thread emits JSON events into a queue. The SSE stream dequeues
and forwards them. A 5s heartbeat event keeps the UI feeling alive during
long rate-limit backoffs; rate-limit events from `fetch_json` are visible too.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from queue import Queue
from threading import Lock, Thread, Timer

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()

_DONE_SENTINEL = object()

# Module-level state, guarded by _state_lock.
# Only ever ONE scan runs. A second /api/scan POST gets 409 until this clears.
_state_lock = Lock()
_scan_state: dict = {
    "running": False,
    "started_at": None,
    "current_subreddit": None,
    "cancel": False,
    "queue": None,  # the current scan's event queue (for /stop to inject 'cancelled')
}


class ScanPayload(BaseModel):
    limit_subreddits: int | None = None
    reset_progress: bool = False


def _state_snapshot() -> dict:
    with _state_lock:
        return {
            "running": _scan_state["running"],
            "started_at": _scan_state["started_at"],
            "current_subreddit": _scan_state["current_subreddit"],
        }


def _run_scan_with_emit(emit, options: ScanPayload) -> None:
    """Execute a Reddit scan and push JSON-serializable events via emit().

    Reads `_scan_state['cancel']` between subreddits; exits early if set.
    Updates `_scan_state['current_subreddit']` so /status reflects progress.
    """
    from inkwell.analyzers.pipeline import analyze_signal
    from inkwell.config import (
        ensure_data_dirs, get_max_post_age_hours, load_filters, load_subreddits,
    )
    from inkwell.filters.rule_filter import apply_pre_filters
    from inkwell.scanners.reddit import RedditScanner
    from inkwell.storage.progress import load_progress, save_progress
    from inkwell.storage.signals import save_signals

    ensure_data_dirs()
    filters = load_filters() or {}
    try:
        subreddits = load_subreddits()
    except Exception as e:
        emit({"kind": "error", "message": f"Failed to load subreddits: {e}"})
        return

    if options.limit_subreddits:
        subreddits = subreddits[: options.limit_subreddits]
    max_age = get_max_post_age_hours(filters)

    progress = load_progress()
    if options.reset_progress:
        progress["completed_subs"] = set()
        progress["processed_ids"] = set()

    emit({
        "kind": "start",
        "subreddit_count": len(subreddits),
        "max_age_hours": max_age,
        "already_done": len(progress["completed_subs"]),
    })

    scanner = RedditScanner()
    collected: list[dict] = []

    # Per-subreddit cap on how many filtered posts we hydrate comments for.
    # Without this, a popular sub like r/aiArt produces 100 posts, most of
    # which pass filters, and hydrating all of them takes minutes of serial
    # 2s-sleep calls. 10 is plenty for signal-finding; tune via filters.yml.
    max_hydrate = int(
        (filters.get("thresholds") or {}).get("max_posts_per_subreddit", 10)
    )

    for i, sub in enumerate(subreddits, 1):
        # Honor cancellation between subreddits.
        with _state_lock:
            if _scan_state["cancel"]:
                emit({"kind": "cancelled", "at": sub, "index": i})
                break
            _scan_state["current_subreddit"] = sub

        if sub in progress["completed_subs"]:
            emit({"kind": "subreddit_skipped", "subreddit": sub, "index": i, "total": len(subreddits)})
            continue

        emit({"kind": "subreddit_start", "subreddit": sub, "index": i, "total": len(subreddits)})

        # Phase 1: fetch posts only (no comments yet).
        try:
            signals = scanner.scan(
                [sub], max_age_hours=max_age, emit=emit, fetch_comments=False,
            )
        except Exception as e:
            emit({"kind": "subreddit_error", "subreddit": sub, "error": str(e)})
            continue

        raw_count = len(signals)

        # Phase 2: filter out posts that wouldn't pass anyway.
        signals = apply_pre_filters(signals, filters)
        emit({
            "kind": "posts_filtered",
            "subreddit": sub,
            "raw": raw_count,
            "kept": len(signals),
        })

        # Phase 3: cap and sort — best score first, so hydration hits the
        # most promising posts first even if we get throttled mid-way.
        if len(signals) > max_hydrate:
            signals = sorted(signals, key=lambda s: s.score, reverse=True)[:max_hydrate]
            emit({
                "kind": "posts_capped",
                "subreddit": sub,
                "cap": max_hydrate,
            })

        # Phase 4: hydrate comments for survivors with visible progress.
        hydrated: list = []
        for pi, signal in enumerate(signals, 1):
            # Honor cancellation between hydrations too.
            with _state_lock:
                if _scan_state["cancel"]:
                    emit({"kind": "cancelled", "at": sub, "index": i, "post_index": pi})
                    return  # exit _run_scan_with_emit entirely

            emit({
                "kind": "post_analyzing",
                "subreddit": sub,
                "index": pi,
                "total": len(signals),
                "title": (signal.title or "")[:80],
            })
            scanner.hydrate_comments(signal, emit=emit)
            hydrated.append(signal)
        signals = hydrated

        emit({
            "kind": "subreddit_done",
            "subreddit": sub,
            "raw": raw_count,
            "kept": len(signals),
        })

        for signal in signals:
            if signal.platform_id in progress["processed_ids"]:
                continue

            analysis = analyze_signal(signal, filters=filters)
            age_hrs = (
                round((time.time() - signal.created_utc) / 3600, 1)
                if signal.created_utc else None
            )
            row = {
                "id": f"reddit_{signal.platform_id}",
                "platform": "reddit",
                "platform_id": signal.platform_id,
                "url": signal.url,
                "title": signal.title,
                "body": signal.body[:500],
                "author": signal.author,
                "subreddit": sub,
                "score": signal.score,
                "reply_count": signal.reply_count,
                "created_utc": signal.created_utc,
                "age_hours": age_hrs,
                "status": signal.status,
                "analysis": {
                    "summary": analysis.summary,
                    "engage": analysis.engage,
                    "why": analysis.why,
                    "coolest_comment": analysis.coolest_comment,
                },
            }
            collected.append(row)
            emit({"kind": "signal", "row": row})
            progress["processed_ids"].add(signal.platform_id)

        progress["completed_subs"].add(sub)
        save_progress(progress)

    if collected:
        save_signals(collected)
    save_progress(progress)

    emit({
        "kind": "done",
        "scanned": len(subreddits),
        "new_signals": len(collected),
        "total_written": progress.get("total_written", 0),
    })


class _Heartbeat:
    """Fires a 'heartbeat' event every `interval` seconds until stopped.

    Self-rearming Timer — lighter than a dedicated thread + sleep loop, and
    cleanly cancellable. Emits elapsed seconds + current subreddit so the UI
    can render a faint pulse even when Reddit is being silent.
    """

    def __init__(self, emit, interval: float = 5.0):
        self._emit = emit
        self._interval = interval
        self._started_at = time.time()
        self._stopped = False
        self._timer: Timer | None = None

    def start(self) -> None:
        self._schedule()

    def stop(self) -> None:
        self._stopped = True
        if self._timer:
            self._timer.cancel()

    def _schedule(self) -> None:
        if self._stopped:
            return
        self._timer = Timer(self._interval, self._fire)
        self._timer.daemon = True
        self._timer.start()

    def _fire(self) -> None:
        if self._stopped:
            return
        try:
            with _state_lock:
                current = _scan_state.get("current_subreddit")
            self._emit({
                "kind": "heartbeat",
                "elapsed_s": round(time.time() - self._started_at, 1),
                "current_subreddit": current,
            })
        except Exception:
            pass
        self._schedule()


@router.get("/scan/status")
async def scan_status():
    return _state_snapshot()


@router.post("/scan/stop")
async def scan_stop():
    with _state_lock:
        if not _scan_state["running"]:
            return {"ok": False, "detail": "No scan is running."}
        _scan_state["cancel"] = True
        q = _scan_state.get("queue")
    # Push a cancelled event so the SSE stream wakes up and reflects it fast.
    if q is not None:
        q.put({"kind": "cancelled", "at": None, "index": None})
    return {"ok": True}


@router.post("/scan")
async def start_scan(payload: ScanPayload | None = None):
    options = payload or ScanPayload()
    q: Queue = Queue()

    with _state_lock:
        if _scan_state["running"]:
            raise HTTPException(
                status_code=409,
                detail="A scan is already running. Stop it or wait for it to finish.",
            )
        _scan_state["running"] = True
        _scan_state["started_at"] = time.time()
        _scan_state["current_subreddit"] = None
        _scan_state["cancel"] = False
        _scan_state["queue"] = q

    heartbeat = _Heartbeat(emit=lambda ev: q.put(ev), interval=5.0)

    def worker():
        heartbeat.start()
        try:
            _run_scan_with_emit(lambda ev: q.put(ev), options)
        except Exception as e:
            logger.exception("Scan failed")
            q.put({"kind": "error", "message": str(e)})
        finally:
            heartbeat.stop()
            with _state_lock:
                _scan_state["running"] = False
                _scan_state["current_subreddit"] = None
                _scan_state["cancel"] = False
                _scan_state["queue"] = None
            q.put(_DONE_SENTINEL)

    Thread(target=worker, daemon=True).start()

    async def event_stream():
        loop = asyncio.get_running_loop()
        try:
            while True:
                item = await loop.run_in_executor(None, q.get)
                if item is _DONE_SENTINEL:
                    break
                yield f"data: {json.dumps(item)}\n\n"
        except asyncio.CancelledError:
            # Client disconnected. Worker + heartbeat finish on their own.
            return

    return StreamingResponse(event_stream(), media_type="text/event-stream")
