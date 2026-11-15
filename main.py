import asyncio
import logging
import os
import json
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
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

# Файл для хранения пользователей (ID: язык)
DB_FILE = "users.json"

def load_users():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_users(users_dict):
    with open(DB_FILE, "w") as f:
        json.dump(users_dict, f)

# Формат базы: {"123456789": {"lang": "ru", "approved": True}}
users_db = load_users()

# ==========================================
# СЛОВАРИ ПЕРЕВОДОВ
# ==========================================
TEXTS = {
    "ru": {
        "choose_lang": "Пожалуйста, выберите язык / Please choose your language:",
        "welcome": "Добро пожаловать в AI Signal Sport! 🤖\n\nДля получения прогнозов от нашей нейросети вам нужно зарегистрироваться.\n\n1️⃣ Нажмите кнопку «Регистрация».\n2️⃣ Пополните баланс от 20$.\n3️⃣ Нажмите «Я зарегистрировался» для проверки.",
        "btn_reg": "Регистрация",
        "btn_check_reg": "Я зарегистрировался / Проверить",
        "btn_paid": "Я пополнил баланс 💲",
        "btn_send_photo": "📸 Отправить скриншот матча",
        "pay_text": "Отлично! Теперь пополните ваш баланс на сайте от 20$.\n\nПосле того как пополните, нажмите кнопку ниже 👇",
        "wait_admin": "⏳ Ваша заявка отправлена на проверку. Ожидайте подтверждения.",
        "approved": "🎉 Ваш доступ активирован! Теперь вы можете отправлять скриншоты матчей для анализа.",
        "rejected": "❌ Ваша заявка на доступ отклонена. Пожалуйста, убедитесь, что вы пополнили баланс от 20$.",
        "no_access": "⛔ У вас нет доступа. Пожалуйста, пополните баланс и дождитесь подтверждения администратора.",
        "analyzing": "⏳ Нейросеть анализирует матч, ожидайте результат...",
        "ai_answer": "🤖 **Анализ нейросети:**\n\n",
        "input_placeholder": "Нажмите кнопку ниже, чтобы отправить фото"
    },
    "en": {
        "choose_lang": "Пожалуйста, выберите язык / Please choose your language:",
        "welcome": "Welcome to AI Signal Sport! 🤖\n\nTo get predictions from our neural network, you need to register.\n\n1️⃣ Click the 'Registration' button.\n2️⃣ Deposit at least $20.\n3️⃣ Click 'I have registered / Check' to verify.",
        "btn_reg": "Registration",
        "btn_check_reg": "I have registered / Check",
        "btn_paid": "I have deposited 💲",
        "btn_send_photo": "📸 Send match screenshot",
        "pay_text": "Great! Now deposit at least $20 on the website.\n\nAfter depositing, click the button below 👇",
        "wait_admin": "⏳ Your request has been sent for review. Please wait for confirmation.",
        "approved": "🎉 Your access is activated! Now you can send match screenshots for analysis.",
        "rejected": "❌ Your access request has been rejected. Please make sure you deposited at least $20.",
        "no_access": "⛔ You do not have access. Please deposit and wait for admin confirmation.",
        "analyzing": "⏳ The neural network is analyzing the match, please wait...",
        "ai_answer": "🤖 **AI Analysis:**\n\n",
        "input_placeholder": "Click the button below to send a photo"
    }
}

def get_lang(user_id):
    return users_db.get(str(user_id), {}).get("lang", "ru")

def is_approved(user_id):
    return users_db.get(str(user_id), {}).get("approved", False)

# ==========================================
# КЛАВИАТУРЫ
# ==========================================
def lang_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"),
                InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")
            ]
        ]
    )

def start_keyboard(lang):
    t = TEXTS[lang]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t["btn_reg"], url=REF_LINK)],
            [InlineKeyboardButton(text=t["btn_check_reg"], callback_data="check_reg")]
        ]
    )

def payment_keyboard(lang):
    t = TEXTS[lang]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t["btn_paid"], callback_data="check_payment")]
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

def forecast_keyboard(lang):
    t = TEXTS[lang]
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t["btn_send_photo"])]],
        resize_keyboard=True,
        input_field_placeholder=t["input_placeholder"]
    )

# ==========================================
# ОБРАБОТЧИКИ
# ==========================================
@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(TEXTS["ru"]["choose_lang"], reply_markup=lang_keyboard())

@router.callback_query(F.data.startswith("lang_"))
async def process_lang(callback: CallbackQuery):
    lang = callback.data.split("_")[1]
    user_id = str(callback.from_user.id)
    
    if user_id not in users_db:
        users_db[user_id] = {"lang": lang, "approved": False}
    else:
        users_db[user_id]["lang"] = lang
    save_users(users_db)
    
    t = TEXTS[lang]
    await callback.message.edit_text(t["welcome"], reply_markup=start_keyboard(lang))
    await callback.answer()

@router.callback_query(F.data == "check_reg")
async def process_check_reg(callback: CallbackQuery):
    lang = get_lang(callback.from_user.id)
    t = TEXTS[lang]
    await callback.message.edit_text(t["pay_text"], reply_markup=payment_keyboard(lang))
    await callback.answer()

@router.callback_query(F.data == "check_payment")
async def process_check_payment(callback: CallbackQuery):
    lang = get_lang(callback.from_user.id)
    t = TEXTS[lang]
    user = callback.from_user
    
    await callback.message.edit_text(t["wait_admin"])
    
    # Отправляем заявку Админу
    await bot.send_message(
        chat_id=ADMIN_ID,
        text=f"🔔 **Новая заявка на доступ**\n\nПользователь: @{user.username}\nID: `{user.id}`\nЯзык: {lang.upper()}",
        reply_markup=admin_keyboard(user.id),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("approve_"))
async def process_approve(callback: CallbackQuery):
    user_id = callback.data.split("_")[1]
    if user_id in users_db:
        users_db[user_id]["approved"] = True
        save_users(users_db)
    
    await callback.message.edit_text("✅ Пользователь одобрен.")
    
    lang = get_lang(user_id)
    try:
        await bot.send_message(
            chat_id=int(user_id), 
            text=TEXTS[lang]["approved"],
            reply_markup=forecast_keyboard(lang)
        )
    except Exception as e:
        await callback.message.answer(f"Ошибка: {e}")
    await callback.answer()

@router.callback_query(F.data.startswith("reject_"))
async def process_reject(callback: CallbackQuery):
    user_id = callback.data.split("_")[1]
    await callback.message.edit_text("❌ Заявка отклонена.")
    
    lang = get_lang(user_id)
    try:
        await bot.send_message(chat_id=int(user_id), text=TEXTS[lang]["rejected"])
    except Exception:
        pass
    await callback.answer()

@router.message(F.photo)
async def handle_photo(message: Message):
    user_id = str(message.from_user.id)
    lang = get_lang(user_id)
    
    if not is_approved(user_id):
        await message.answer(TEXTS[lang]["no_access"])
        return

    await message.answer(TEXTS[lang]["analyzing"])
    
    # Пересылаем фото Админу
    await bot.send_photo(
        chat_id=ADMIN_ID,
        photo=message.photo[-1].file_id,
        caption=f"Запрос прогноза от @{message.from_user.username} (ID: {user_id}).\nLang: {lang.upper()}\n\nОтветьте (Reply) на это сообщение вашим прогнозом."
    )

@router.message(F.reply_to_message, F.from_user.id == ADMIN_ID)
async def handle_admin_reply(message: Message):
    if message.reply_to_message.caption and "ID:" in message.reply_to_message.caption:
        try:
            # Вытаскиваем ID и язык
            caption = message.reply_to_message.caption
            user_id_str = caption.split("ID: ")[1].split(")")[0]
            lang = "en" if "Lang: EN" in caption else "ru"
            
            # Отправляем прогноз пользователю
            await bot.send_message(
                chat_id=int(user_id_str),
                text=f"{TEXTS[lang]['ai_answer']}{message.text}"
            )
            await message.reply("✅ Прогноз отправлен!")
        except Exception as e:
            await message.reply(f"Ошибка: {e}")

# ==========================================
# ЗАПУСК
# ==========================================
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
