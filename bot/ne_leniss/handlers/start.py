from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    WebAppInfo,
)

from ne_leniss.config import Settings
from ne_leniss.repository import Repository

router = Router()

WELCOME = (
    "Привет 👋\n\n"
    "Я помогу с трекингом привычек. Каждое утро в 09:00 МСК пришлю чек-лист "
    "за вчера и спрошу планы на сегодня.\n\n"
    "Команды:\n"
    "/note <текст> — добавить заметку в журнал сегодня\n"
    "/plan <дата> <текст> — запланировать на любой день\n"
    "/app — открыть приложение с календарём и стриками\n\n"
    "Открой приложение, чтобы видеть свой календарь:"
)

HELP = (
    "Команды:\n"
    "/note <текст> — добавить заметку в журнал сегодня\n"
    "/plan <дата> <текст> — запланировать на любой день\n"
    "    дата: today, tomorrow, +N, YYYY-MM-DD или DD.MM\n"
    "/app — открыть приложение с календарём и стриками"
)


def _open_app_keyboard(webapp_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Открыть приложение", web_app=WebAppInfo(url=webapp_url))]
        ]
    )


@router.message(CommandStart())
async def cmd_start(message: Message, repo: Repository, settings: Settings) -> None:
    user = message.from_user
    if user is None:
        return
    existing = await repo.get_user(user.id)
    await repo.get_or_create_user(
        tg_id=user.id,
        username=user.username,
        first_name=user.first_name,
    )
    text = WELCOME if existing is None else HELP
    await message.answer(text, reply_markup=_open_app_keyboard(settings.webapp_url))
