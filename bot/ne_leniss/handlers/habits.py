from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message

from ne_leniss.habits import (
    encode_habits,
    parse_habits_input,
    user_habits_or_default,
)
from ne_leniss.repository import Repository

router = Router()


class HabitsStates(StatesGroup):
    awaiting_new = State()


@router.message(Command("habits"))
async def cmd_habits(message: Message, repo: Repository, state: FSMContext) -> None:
    if message.from_user is None:
        return
    user = await repo.get_user(message.from_user.id)
    if user is None or not user.habits_json:
        await message.answer(
            "Ты ещё не проходил онбординг. Жми /start чтобы настроить привычки."
        )
        return
    current = user_habits_or_default(user.habits_json)
    listing = "\n".join(f"• {label}" for _, label in current)
    await message.answer(
        f"Твои сейчас привычки:\n{listing}\n\n"
        "Хочешь изменить? Напиши новый список через запятую — обновлю с сегодняшнего дня.\n"
        "Прошлые дни оставлю как есть — их прогресс сохранится.\n\n"
        "Передумал — /cancel."
    )
    await state.set_state(HabitsStates.awaiting_new)


@router.message(HabitsStates.awaiting_new, F.text == "/cancel")
async def on_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Окей, оставил как есть.")


@router.message(HabitsStates.awaiting_new)
async def on_new_habits(message: Message, repo: Repository, state: FSMContext) -> None:
    if message.from_user is None or not message.text:
        return
    if message.text.startswith("/"):
        await message.answer("Похоже на команду. Если передумал — /cancel.")
        return
    habits = parse_habits_input(message.text)
    if len(habits) < 3:
        await message.answer("Маловато. Напиши минимум 3 привычки через запятую.")
        return
    if len(habits) > 8:
        habits = habits[:8]
        await message.answer("Взял первые 8 — остальные добавим позже.")

    await repo.set_user_habits(message.from_user.id, encode_habits(habits))
    listing = "\n".join(f"• {label}" for _, label in habits)
    await message.answer(
        f"✓ обновил! С сегодняшнего дня твой чек-лист:\n{listing}\n\n"
        "Прошлые дни оставил как есть — их прогресс и стрики по старым "
        "привычкам сохранены в календаре, но в разделе «Стрики» теперь "
        "показываются только актуальные."
    )
    await state.clear()
