# autonomy.py — Scheduled background task runner.
#
# Two daily jobs registered via python-telegram-bot's built-in job_queue (APScheduler):
#   morning_brief  — 12:00 UTC (8am ET): review goals, do research, report
#   midday_tick    — 17:00 UTC (1pm ET): check for anything actionable mid-day
#
# Each job calls process_turn() with a crafted task prompt and empty history.
# Output sent to owner only if non-trivial. Silence is correct when nothing happened.
#
# Jarvis also reaches out immediately (outside scheduled runs) via telegram_notify
# whenever it discovers something worth flagging — that behavior is driven by SOUL.md
# and prompt.py guidance, not by this file.

import asyncio
import logging

from telegram.ext import ContextTypes

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_OWNER_ID
from brain import process_turn

logger = logging.getLogger(__name__)

_MORNING_TASK = (
    "Autonomy tick — morning brief. "
    "Check your active goals with goal_manager. "
    "Do research on anything relevant: new Richmond businesses opening, "
    "updates on prospect targets (Susie's Deli, Mongrel, Lafayette Tavern, Verdalina, Yummvees), "
    "local competitor agencies, or anything in the news that affects the pipeline. "
    "Update goal progress if anything has changed. "
    "Send a concise brief of what you found and what you're doing about it. "
    "If there is genuinely nothing new worth reporting, send nothing — silence is correct."
)

_MIDDAY_TASK = (
    "Autonomy tick — midday check. "
    "Quick scan: is there any goal that needs action right now? "
    "Any research from this morning worth following up on? "
    "Any time-sensitive opportunity in the pipeline? "
    "If yes, act on it and send a brief note. "
    "If nothing needs doing, send nothing."
)


async def _run_task(context: ContextTypes.DEFAULT_TYPE, task_prompt: str, label: str) -> None:
    loop = asyncio.get_event_loop()
    try:
        logger.info("Autonomy tick: %s", label)
        reply = await loop.run_in_executor(None, process_turn, task_prompt, [])
        if reply and reply.strip():
            await context.bot.send_message(chat_id=TELEGRAM_OWNER_ID, text=reply)
            logger.info("Autonomy tick %s: sent reply (%d chars)", label, len(reply))
        else:
            logger.info("Autonomy tick %s: nothing to report", label)
    except Exception as e:
        logger.error("Autonomy tick %s failed: %s", label, e)


async def morning_brief(context: ContextTypes.DEFAULT_TYPE) -> None:
    await _run_task(context, _MORNING_TASK, "morning_brief")


async def midday_tick(context: ContextTypes.DEFAULT_TYPE) -> None:
    await _run_task(context, _MIDDAY_TASK, "midday_tick")
