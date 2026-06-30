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


@router.message(Command("app"))
async def cmd_app(message: Message, settings: Settings) -> None:
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Открыть приложение", web_app=WebAppInfo(url=settings.webapp_url))]
        ]
    )
    await message.answer("Открой приложение для просмотра календаря и стриков:", reply_markup=kb)
