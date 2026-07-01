from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    WebAppInfo,
)

from ne_leniss.config import Settings
from ne_leniss.handlers.onboarding import start_onboarding
from ne_leniss.repository import Repository

router = Router()

HELP = (
    "Команды:\n"
    "• /note — заметка в журнал сегодня\n"
    "• /plan — запланировать на любой день\n"
    "• /habits — изменить список привычек\n"
    "• /app — открыть приложение\n"
    "• /reset_onboarding — пройти онбординг заново"
)


def _open_app_keyboard(webapp_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Открыть приложение", web_app=WebAppInfo(url=webapp_url))]
        ]
    )


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    repo: Repository,
    settings: Settings,
    state: FSMContext,
) -> None:
    if message.from_user is None:
        return
    user = await repo.get_or_create_user(
        tg_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )
    if not user.habits_json:
        # Not onboarded yet — start the welcome flow
        await start_onboarding(message, state)
        return
    await message.answer(HELP, reply_markup=_open_app_keyboard(settings.webapp_url))
