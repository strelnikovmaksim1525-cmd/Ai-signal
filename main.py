
import os
import asyncio
import logging
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)

# ==================================================
# НАСТРОЙКИ
# ==================================================

# Токен и ID указываются в Railway -> Variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# ==================================================
# ХРАНЕНИЕ ОДОБРЕННЫХ ПОЛЬЗОВАТЕЛЕЙ
# ==================================================

APPROVED_FILE = Path("approved_users.txt")


def load_approved_users():
    if not APPROVED_FILE.exists():
        APPROVED_FILE.write_text("", encoding="utf-8")

    users = set()

    for line in APPROVED_FILE.read_text(
        encoding="utf-8"
    ).splitlines():
        try:
            users.add(int(line.strip()))
        except ValueError:
            continue

    return users


approved_users = load_approved_users()


def save_approved_users():
    APPROVED_FILE.write_text(
        "\n".join(map(str, sorted(approved_users))),
        encoding="utf-8"
    )


# ==================================================
# ХРАНЕНИЕ ЗАПРОСОВ
# ==================================================

# message_id сообщения с фотографией в чате администратора
# -> Telegram ID пользователя

photo_requests = {}


# ==================================================
# ИНИЦИАЛИЗАЦИЯ
# ==================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# ==================================================
# КЛАВИАТУРЫ
# ==================================================

def main_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Регистрация",
                    url="https://lkdq.cc/392889"
                )
            ],
            [
                InlineKeyboardButton(
                    text="Отправить скриншот матча",
                    callback_data="check_payment"
                )
            ]
        ]
    )


def forecast_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Получить анализ",
                    callback_data="get_forecast"
                )
            ]
        ]
    )


def admin_keyboard(user_id: int):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Одобрить",
                    callback_data=f"approve_{user_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data=f"reject_{user_id}"
                )
            ]
        ]
    )


# ==================================================
# START
# ==================================================

@dp.message(CommandStart())
async def start(message: Message):

    await message.answer(
        "Добро пожаловать!\n\n"
        "Здесь вы можете отправить скриншот "
        "спортивного матча для анализа.",
        reply_markup=main_keyboard()
    )


# ==================================================
# ЗАЯВКА ПОЛЬЗОВАТЕЛЯ
# ==================================================

@dp.callback_query(F.data == "check_payment")
async def send_application(callback: CallbackQuery):

    user = callback.from_user

    if user.id in approved_users:
        await callback.message.answer(
            "Ваш доступ уже подтверждён.",
            reply_markup=forecast_keyboard()
        )
        await callback.answer()
        return

    username = (
        f"@{user.username}"
        if user.username
        else "без username"
    )

    try:
        await bot.send_message(
            ADMIN_ID,
            f"Новая заявка на доступ.\n\n"
            f"Пользователь: {username}\n"
            f"ID: {user.id}",
            reply_markup=admin_keyboard(user.id)
        )

        await callback.message.answer(
            "Заявка отправлена администратору. "
            "Ожидайте подтверждения."
        )

    except Exception:
        logging.exception("Ошибка отправки заявки")

        await callback.message.answer(
            "Не удалось отправить заявку. "
            "Попробуйте позже."
        )

    await callback.answer()


# ==================================================
# ОДОБРЕНИЕ ПОЛЬЗОВАТЕЛЯ
# ==================================================

@dp.callback_query(F.data.startswith("approve_"))
async def approve_user(callback: CallbackQuery):

    if callback.from_user.id != ADMIN_ID:
        await callback.answer(
            "Нет прав.",
            show_alert=True
        )
        return

    try:
        user_id = int(
            callback.data.split("_", 1)[1]
        )
    except (ValueError, IndexError):
        await callback.answer("Некорректный ID.")
        return

    already_approved = user_id in approved_users

    approved_users.add(user_id)
    save_approved_users()

    try:
        await callback.message.edit_text(
            f"✅ Доступ одобрен.\n"
            f"ID пользователя: {user_id}"
        )
    except Exception:
        pass

    if already_approved:
        await callback.answer(
            "Пользователь уже одобрен."
        )
        return

    try:
        await bot.send_message(
            user_id,
            "Ваш доступ подтверждён!\n\n"
            "Теперь вы можете отправить скриншот "
            "спортивного матча для анализа.",
            reply_markup=forecast_keyboard()
        )

        await callback.answer("Доступ выдан.")

    except Exception:
        logging.exception(
            "Не удалось уведомить пользователя"
        )

        await callback.answer(
            "Доступ сохранён, но уведомление не доставлено.",
            show_alert=True
        )


# ==================================================
# ОТКЛОНЕНИЕ ЗАЯВКИ
# ==================================================

@dp.callback_query(F.data.startswith("reject_"))
async def reject_user(callback: CallbackQuery):

    if callback.from_user.id != ADMIN_ID:
        await callback.answer(
            "Нет прав.",
            show_alert=True
        )
        return

    try:
        user_id = int(
            callback.data.split("_", 1)[1]
        )
    except (ValueError, IndexError):
        await callback.answer("Некорректный ID.")
        return

    try:
        await callback.message.edit_text(
            f"❌ Заявка отклонена.\n"
            f"ID пользователя: {user_id}"
        )
    except Exception:
        pass

    try:
        await bot.send_message(
            user_id,
            "Ваша заявка отклонена администратором."
        )
    except Exception:
        logging.exception(
            "Не удалось уведомить пользователя"
        )

    await callback.answer("Заявка отклонена.")


# ==================================================
# ПОЛУЧЕНИЕ АНАЛИЗА
# ==================================================

@dp.callback_query(F.data == "get_forecast")
async def get_forecast(callback: CallbackQuery):

    user_id = callback.from_user.id

    if user_id not in approved_users:
        await callback.answer(
            "Сначала получите подтверждение доступа.",
            show_alert=True
        )
        return

    await callback.message.answer(
        "Пожалуйста, отправьте скриншот "
        "спортивного матча."
    )

    await callback.answer()


# ==================================================
# ПОЛУЧЕНИЕ ФОТОГРАФИИ
# ==================================================

@dp.message(F.photo)
async def receive_photo(message: Message):

    user_id = message.from_user.id

    if user_id not in approved_users:
        await message.answer("Нет доступа.")
        return

    username = (
        f"@{message.from_user.username}"
        if message.from_user.username
        else "без username"
    )

    await message.answer(
        "⏳ Скриншот получен. "
        "Администратор анализирует матч."
    )

    try:
        admin_message = await bot.send_photo(
            chat_id=ADMIN_ID,
            photo=message.photo[-1].file_id,
            caption=(
                "📩 Новый запрос спортивного анализа\n\n"
                f"Пользователь: {username}\n"
                f"ID: {user_id}\n\n"
                "Ответьте на это сообщение через Reply."
            )
        )

        photo_requests[
            admin_message.message_id
        ] = user_id

    except Exception:
        logging.exception(
            "Ошибка отправки фотографии администратору"
        )

        await message.answer(
            "Не удалось передать фотографию. "
            "Попробуйте позже."
        )


# ==================================================
# ОТВЕТ АДМИНИСТРАТОРА ЧЕРЕЗ REPLY
# ==================================================

@dp.message(F.reply_to_message)
async def admin_reply(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    original_message = message.reply_to_message

    user_id = photo_requests.get(
        original_message.message_id
    )

    if not user_id:
        return

    answer_text = message.text or message.caption

    if not answer_text:
        await message.answer(
            "Отправьте текстовый ответ."
        )
        return

    try:
        await bot.send_message(
            chat_id=user_id,
            text=(
                "📊 Ответ по вашему спортивному анализу:\n\n"
                f"{answer_text}"
            )
        )

        await message.reply(
            "✅ Ответ отправлен пользователю."
        )

        photo_requests.pop(
            original_message.message_id,
            None
        )

    except Exception:
        logging.exception(
            "Ошибка доставки ответа пользователю"
        )

        await message.reply(
            "Не удалось отправить ответ пользователю."
        )


# ==================================================
# ЗАПУСК
# ==================================================

async def main():

    if not BOT_TOKEN:
        raise RuntimeError(
            "Не задан BOT_TOKEN в Railway Variables."
        )

    logging.info("Бот запущен.")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
  
