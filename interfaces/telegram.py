# interfaces/telegram.py — Telegram bot interface for jarvis-v3.
#
# Owner-only: all messages and commands silently dropped if not from TELEGRAM_OWNER_ID.
# process_turn() is synchronous — wrapped via run_in_executor to avoid blocking the event loop.
# Per-chat asyncio.Queue serializes concurrent messages from the same chat.
#
# History: conversation history loaded/saved per chat via store/history.py.
# Episodes: each exchange recorded to Xeon episodic memory (fire-and-forget).
#
# Commands: /start, /status, /clear

import asyncio
import logging

from telegram import Update, BotCommand
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_OWNER_ID, MODEL
from brain import process_turn
from store.history import load_history, save_history, clear_history
from memory.episodes import record_episode

logger = logging.getLogger(__name__)

_queues: dict[int, asyncio.Queue] = {}
_tasks: dict[int, asyncio.Task] = {}
_MAX_LEN = 4096


def _split(text: str) -> list[str]:
    if len(text) <= _MAX_LEN:
        return [text]
    chunks = []
    while text:
        if len(text) <= _MAX_LEN:
            chunks.append(text)
            break
        split_at = text.rfind('\n', 0, _MAX_LEN)
        if split_at == -1:
            split_at = _MAX_LEN
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip('\n')
    return chunks


def _is_owner(update: Update) -> bool:
    return bool(update.effective_user and update.effective_user.id == TELEGRAM_OWNER_ID)


async def _process_queue(queue: asyncio.Queue) -> None:
    loop = asyncio.get_event_loop()
    while True:
        update, user_text, chat_id = await queue.get()
        try:
            await update.effective_chat.send_action(ChatAction.TYPING)

            # Load history, run turn, save updated history
            history = load_history(chat_id)
            reply = await loop.run_in_executor(None, process_turn, user_text, history)
            for chunk in _split(reply):
                await update.message.reply_text(chunk)

            save_history(chat_id, history + [
                {"role": "user", "content": user_text},
                {"role": "assistant", "content": reply},
            ])

            # Record episode to Xeon (fire-and-forget, non-fatal)
            loop.run_in_executor(None, record_episode, user_text, reply)

        except Exception as e:
            logger.error("Error processing message: %s", e)
            await update.message.reply_text("Error processing your message.")
        finally:
            queue.task_done()


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_owner(update):
        return
    logger.info("Message received from owner: %s", update.message.text[:50])
    chat_id = update.effective_chat.id
    if chat_id not in _queues:
        queue: asyncio.Queue = asyncio.Queue()
        _queues[chat_id] = queue
        task = asyncio.create_task(_process_queue(queue))
        _tasks[chat_id] = task
    await _queues[chat_id].put((update, update.message.text, chat_id))


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_owner(update):
        return
    await update.message.reply_text("Jarvis v3 online.")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_owner(update):
        return
    await update.message.reply_text(f"Running. Model: {MODEL}")


async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_owner(update):
        return
    chat_id = update.effective_chat.id
    cleared = clear_history(chat_id)
    await update.message.reply_text(
        "Conversation history cleared." if cleared else "No history to clear."
    )


async def post_init(app: Application) -> None:
    await app.bot.set_my_commands([
        BotCommand("start", "Start the bot"),
        BotCommand("status", "Check bot status"),
        BotCommand("clear", "Clear conversation history"),
    ])


async def post_stop(app: Application) -> None:
    for task in _tasks.values():
        task.cancel()
    _tasks.clear()


def run_bot() -> None:
    logging.basicConfig(level=logging.INFO)
    app = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .post_stop(post_stop)
        .build()
    )
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("clear", cmd_clear))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling(drop_pending_updates=False)
