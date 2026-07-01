import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    WebAppInfo,
)

from ne_leniss.config import Settings

router = Router()
log = logging.getLogger("ne_leniss.app")


def app_keyboard(webapp_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Открыть приложение", web_app=WebAppInfo(url=webapp_url))]
        ]
    )


async def pin_app_shortcut(message: Message, settings: Settings) -> None:
    """Send an Open-App shortcut message and pin it to the top of the chat.
    Idempotent-ish: Telegram allows pin overwrite; failure is swallowed
    (bot may lack pin rights in a group, though we only ever DM).
    """
    try:
        pin_msg = await message.answer(
            "🚀 Быстрый доступ к твоему Календарю привычек",
            reply_markup=app_keyboard(settings.webapp_url),
        )
        await message.bot.pin_chat_message(
            chat_id=message.chat.id,
            message_id=pin_msg.message_id,
            disable_notification=True,
        )
    except Exception:
        log.exception("failed to pin app shortcut for chat %s", message.chat.id)


@router.message(Command("app"))
async def cmd_app(message: Message, settings: Settings) -> None:
    await message.answer(
        "Открой приложение для просмотра календаря и стриков:",
        reply_markup=app_keyboard(settings.webapp_url),
    )


@router.message(Command("pin"))
async def cmd_pin(message: Message, settings: Settings) -> None:
    await pin_app_shortcut(message, settings)
