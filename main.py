import asyncio
import logging
import os
import json
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import Command

# ==========================================
# НАСТРОЙКИ
# ==========================================
# Вставь сюда свою партнерскую ссылку на 1win!
REF_LINK = "https://lkdq.cc/392889" 

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# Файл для хранения одобренных пользователей (чтобы не терялись при перезапуске)
DB_FILE = "users.json"

def load_users():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_users(users_set):
    with open(DB_FILE, "w") as f:
        json.dump(list(users_set), f)

approved_users = load_users()

# ==========================================
# КЛАВИАТУРЫ
# ==========================================
def start_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Регистрация", url=REF_LINK)],
            [InlineKeyboardButton(text="Я зарегистрировался / Проверить", callback_data="check_reg")]
        ]
    )

def payment_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Я пополнил баланс 💲", callback_data="check_payment")]
        ]
    )

def admin_keyboard(user_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_{user_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{user_id}")
            ]
        ]
    )

def forecast_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📸 Отправить скриншот матча")]],
        resize_keyboard=True,
        input_field_placeholder="Нажмите кнопку ниже, чтобы отправить фото"
    )

# ==========================================
# ОБРАБОТЧИКИ КОМАНД
# ==========================================
@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Добро пожаловать в AI Signal Sport! 🤖\n\n"
        "Для получения прогнозов от нашей нейросети вам нужно зарегистрироваться.\n\n"
        "1️⃣ Нажмите кнопку «Регистрация».\n"
        "2️⃣ Пополните баланс от 20$.\n"
        "3️⃣ Нажмите «Я зарегистрировался» для проверки.",
        reply_markup=start_keyboard()
    )

# ==========================================
# ОБРАБОТЧИКИ КНОПОК (CALLBACKS)
# ==========================================
@router.callback_query(F.data == "check_reg")
async def process_check_reg(callback: CallbackQuery):
    await callback.message.edit_text(
        "Отлично! Теперь пополните ваш баланс на сайте от 20$.\n\n"
        "После того как пополните, нажмите кнопку ниже 👇",
        reply_markup=payment_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "check_payment")
async def process_check_payment(callback: CallbackQuery):
    user = callback.from_user
    await callback.message.edit_text("⏳ Ваша заявка отправлена на проверку. Ожидайте подтверждения.")
    
    # Отправляем заявку Админу
    await bot.send_message(
        chat_id=ADMIN_ID,
        text=f"🔔 **Новая заявка на доступ**\n\nПользователь: @{user.username}\nID: `{user.id}`",
        reply_markup=admin_keyboard(user.id),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("approve_"))
async def process_approve(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    approved_users.add(user_id)
    save_users(approved_users)
    
    await callback.message.edit_text("✅ Пользователь одобрен.")
    try:
        await bot.send_message(
            chat_id=user_id, 
            text="🎉 Ваш доступ активирован! Теперь вы можете отправлять скриншоты матчей для анализа.",
            reply_markup=forecast_keyboard()
        )
    except Exception as e:
        await callback.message.answer(f"Ошибка при отправке сообщения юзеру: {e}")
    await callback.answer()

@router.callback_query(F.data.startswith("reject_"))
async def process_reject(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[1])
    await callback.message.edit_text("❌ Заявка отклонена.")
    try:
        await bot.send_message(
            chat_id=user_id, 
            text="❌ Ваша заявка на доступ отклонена. Пожалуйста, убедитесь, что вы пополнили баланс от 20$."
        )
    except Exception:
        pass
    await callback.answer()

# ==========================================
# ОБРАБОТКА ФОТО ОТ ПОЛЬЗОВАТЕЛЕЙ
# ==========================================
@router.message(F.photo)
async def handle_photo(message: Message):
    user_id = message.from_user.id
    
    if user_id not in approved_users:
        await message.answer("⛔ У вас нет доступа. Пожалуйста, пополните баланс и дождитесь подтверждения администратора.")
        return

    await message.answer("⏳ Нейросеть анализирует матч, ожидайте результат...")
    
    # Пересылаем фото Админу
    await bot.send_photo(
        chat_id=ADMIN_ID,
        photo=message.photo[-1].file_id,
        caption=f"Запрос прогноза от @{message.from_user.username} (ID: {user_id}).\n\nОтветьте (Reply) на это сообщение вашим прогнозом."
    )

# ==========================================
# ОТВЕТ АДМИНА (REPLY НА ФОТО)
# ==========================================
@router.message(F.reply_to_message, F.from_user.id == ADMIN_ID)
async def handle_admin_reply(message: Message):
    if message.reply_to_message.caption and "ID:" in message.reply_to_message.caption:
        try:
            # Вытаскиваем ID пользователя из текста пересланного фото
            user_id_str = message.reply_to_message.caption.split("ID: ")[1].split(")")[0]
            target_user_id = int(user_id_str)
            
            # Отправляем прогноз пользователю
            await bot.send_message(
                chat_id=target_user_id,
                text=f"🤖 **Анализ нейросети:**\n\n{message.text}"
            )
            await message.reply("✅ Прогноз успешно отправлен пользователю!")
        except Exception as e:
            await message.reply(f"Ошибка: не удалось отправить сообщение. {e}")

# ==========================================
# ЗАПУСК
# ==========================================
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
