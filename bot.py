import asyncio
import logging
import os
from datetime import datetime, timedelta
from groq import Groq
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, LabeledPrice, PreCheckoutQuery

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
client = Groq(api_key=GROQ_API_KEY)

users = {}
HOURLY_LIMIT = 10
PREMIUM_STARS = 50

TEXTS = {
    "ua": {
        "welcome": "👋 *Привіт!*\n\nЯ — твій особистий ШІ-помічник 🤖\nГотовий відповісти на будь-яке запитання!\n\n━━━━━━━━━━━━━━\n📌 *Команди:*\n❓ /help — підказки\n📊 /stats — статистика\n💎 /premium — преміум\n🗑 /clear — очистити історію\n━━━━━━━━━━━━━━",
        "cleared": "🗑 Історію очищено! Починаємо з чистого аркуша ✨",
        "thinking": "⏳ Думаю...",
        "limit": "🚫 *Ліміт вичерпано!*\n\nТи використав усі 10 запитів цієї години 😔\nСпробуй знову через {minutes} хв ⏱\n\n💎 Або купи преміум за *50 Stars* і отримай *безліміт на 30 днів!* 🚀",
        "stats": "📊 *Твоя статистика*\n━━━━━━━━━━━━━━\n📝 Запитів за годину: *{req}/10*\n🏷 Статус: *{status}*\n━━━━━━━━━━━━━━",
        "premium_info": "💎 *Преміум підписка*\n━━━━━━━━━━━━━━\n⭐ Ціна: *50 Telegram Stars*\n♾ Безліміт запитів на *30 днів*\n⚡ Без обмежень і черг\n━━━━━━━━━━━━━━",
        "premium_ok": "🎉 *Вітаємо!*\n\nПреміум активовано на 30 днів!\nДякуємо за підтримку 💜",
        "free": "🆓 Безкоштовний",
        "prem": "💎 Преміум",
        "buy": "💎 Купити преміум",
        "help": "🤖 *Що я вмію:*\n━━━━━━━━━━━━━━\n💬 Відповідати на запитання\n📚 Пояснювати складні теми\n✍️ Допомагати з текстами та ідеями\n🌍 Перекладати та редагувати\n💻 Писати код\n━━━━━━━━━━━━━━\n📊 /stats — статистика\n💎 /premium — преміум\n🗑 /clear — очистити історію",
    },
    "ru": {
        "welcome": "👋 *Привет!*\n\nЯ — твой личный ИИ-помощник 🤖\nГотов ответить на любой вопрос!\n\n━━━━━━━━━━━━━━\n📌 *Команды:*\n❓ /help — подсказки\n📊 /stats — статистика\n💎 /premium — премиум\n🗑 /clear — очистить историю\n━━━━━━━━━━━━━━",
        "cleared": "🗑 История очищена! Начинаем с чистого листа ✨",
        "thinking": "⏳ Думаю...",
        "limit": "🚫 *Лимит исчерпан!*\n\nТы использовал все 10 запросов этого часа 😔\nПопробуй снова через {minutes} мин ⏱\n\n💎 Или купи премиум за *50 Stars* и получи *безлимит на 30 дней!* 🚀",
        "stats": "📊 *Твоя статистика*\n━━━━━━━━━━━━━━\n📝 Запросов за час: *{req}/10*\n🏷 Статус: *{status}*\n━━━━━━━━━━━━━━",
        "premium_info": "💎 *Премиум подписка*\n━━━━━━━━━━━━━━\n⭐ Цена: *50 Telegram Stars*\n♾ Безлимит запросов на *30 дней*\n⚡ Без ограничений и очередей\n━━━━━━━━━━━━━━",
        "premium_ok": "🎉 *Поздравляем!*\n\nПремиум активирован на 30 дней!\nСпасибо за поддержку 💜",
        "free": "🆓 Бесплатный",
        "prem": "💎 Премиум",
        "buy": "💎 Купить премиум",
        "help": "🤖 *Что я умею:*\n━━━━━━━━━━━━━━\n💬 Отвечать на вопросы\n📚 Объяснять сложные темы\n✍️ Помогать с текстами и идеями\n🌍 Переводить и редактировать\n💻 Писать код\n━━━━━━━━━━━━━━\n📊 /stats — статистика\n💎 /premium — премиум\n🗑 /clear — очистить историю",
    },
}


def get_user(uid):
    if uid not in users:
        users[uid] = {"lang": None, "req": 0, "window_start": None, "premium_until": None, "history": []}
    u = users[uid]
    now = datetime.now()
    if u["window_start"] is None or now - u["window_start"] >= timedelta(hours=1):
        u["req"] = 0
        u["window_start"] = now
    return u


def minutes_left(u):
    now = datetime.now()
    elapsed = now - u["window_start"]
    remaining = timedelta(hours=1) - elapsed
    return max(1, int(remaining.total_seconds() // 60))


def is_premium(u):
    return bool(u["premium_until"] and u["premium_until"] >= datetime.now().date())


def lang_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🇺🇦 Українська", callback_data="lang_ua"),
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"),
    ]])


def prem_kb(lang):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=TEXTS[lang]["buy"], callback_data="buy_premium"),
    ]])


@dp.message(Command("start"))
async def cmd_start(message: Message):
    get_user(message.from_user.id)["history"].clear()
    await message.answer("🌍 Обери мову / Выбери язык:", reply_markup=lang_kb())


@dp.callback_query(F.data.startswith("lang_"))
async def set_lang(callback: CallbackQuery):
    lang = callback.data.split("_")[1]
    get_user(callback.from_user.id)["lang"] = lang
    await callback.message.edit_text(TEXTS[lang]["welcome"], parse_mode="Markdown")


@dp.message(Command("help"))
async def cmd_help(message: Message):
    u = get_user(message.from_user.id)
    lang = u["lang"] or "ua"
    await message.answer(TEXTS[lang]["help"], parse_mode="Markdown")


@dp.message(Command("clear"))
async def cmd_clear(message: Message):
    u = get_user(message.from_user.id)
    lang = u["lang"] or "ua"
    u["history"].clear()
    await message.answer(TEXTS[lang]["cleared"])


@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    u = get_user(message.from_user.id)
    lang = u["lang"] or "ua"
    status = TEXTS[lang]["prem"] if is_premium(u) else TEXTS[lang]["free"]
    await message.answer(TEXTS[lang]["stats"].format(req=u["req"], status=status), parse_mode="Markdown")


@dp.message(Command("premium"))
async def cmd_premium(message: Message):
    u = get_user(message.from_user.id)
    lang = u["lang"] or "ua"
    await message.answer(TEXTS[lang]["premium_info"], parse_mode="Markdown", reply_markup=prem_kb(lang))


@dp.callback_query(F.data == "buy_premium")
async def buy_premium(callback: CallbackQuery):
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title="💎 Premium",
        description="30 days unlimited access",
        payload="premium_30days",
        currency="XTR",
        prices=[LabeledPrice(label="Premium", amount=PREMIUM_STARS)],
    )


@dp.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(query.id, ok=True)


@dp.message(F.successful_payment)
async def payment_done(message: Message):
    u = get_user(message.from_user.id)
    lang = u["lang"] or "ua"
    u["premium_until"] = (datetime.now() + timedelta(days=30)).date()
    await message.answer(TEXTS[lang]["premium_ok"], parse_mode="Markdown")


@dp.message()
async def handle_message(message: Message):
    if not message.text:
        return
    u = get_user(message.from_user.id)
    if not u["lang"]:
        await message.answer("🌍 Обери мову / Выбери язык:", reply_markup=lang_kb())
        return
    lang = u["lang"]
    if not is_premium(u) and u["req"] >= HOURLY_LIMIT:
        text = TEXTS[lang]["limit"].format(minutes=minutes_left(u))
        await message.answer(text, parse_mode="Markdown", reply_markup=prem_kb(lang))
        return
    u["history"].append({"role": "user", "content": message.text})
    thinking = await message.answer(TEXTS[lang]["thinking"])
    try:
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": "Ти корисний помічник. Відповідай на мові користувача."}] + u["history"][-20:],
        )
        reply = response.choices[0].message.content
        u["history"].append({"role": "assistant", "content": reply})
        u["req"] += 1
        await thinking.delete()
        await message.answer(reply)
    except Exception as e:
        await thinking.delete()
        await message.answer(str(e)[:300])


async def main():
    print("Bot started!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
    
