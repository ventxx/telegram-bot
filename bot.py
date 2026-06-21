import asyncio
import logging
import os
from datetime import date, timedelta
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
FREE_LIMIT = 15
PREMIUM_STARS = 50

TEXTS = {
    "ua": {
        "welcome": "Pryvit! Ya ShI-pomichnyk. Napyshy bud-yake zapytannya!",
        "cleared": "Istoriyu ochyshcheno!",
        "thinking": "Dumayu...",
        "limit": "Limit vycherpano! Kupy premium dlya bezlimitu na 30 dniv.",
        "stats": "Zapytiv sohodni: {req}/15\nStatus: {status}",
        "premium_info": "Premium - 50 Stars\nBezlimit na 30 dniv!",
        "premium_ok": "Premium aktyvovano na 30 dniv!",
        "free": "Bezkoshtovnyy",
        "prem": "Premium",
        "buy": "Kupyty premium",
    },
    "ru": {
        "welcome": "Privet! Ya II-pomoshnik. Napishi lyuboy vopros!",
        "cleared": "Istoriya ochishchena!",
        "thinking": "Dumayu...",
        "limit": "Limit ischerpan! Kupi premium dlya bezlimita na 30 dney.",
        "stats": "Zaprosov segodnya: {req}/15\nStatus: {status}",
        "premium_info": "Premium - 50 Stars\nBezlimit na 30 dney!",
        "premium_ok": "Premium aktivirovan na 30 dney!",
        "free": "Besplatnyy",
        "prem": "Premium",
        "buy": "Kupit premium",
    },
}


def get_user(uid):
    if uid not in users:
        users[uid] = {"lang": None, "req": 0, "last_date": None, "premium_until": None, "history": []}
    u = users[uid]
    today = date.today()
    if u["last_date"] != today:
        u["req"] = 0
        u["last_date"] = today
    return u


def is_premium(u):
    return bool(u["premium_until"] and u["premium_until"] >= date.today())


def lang_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="UA Ukrainska", callback_data="lang_ua"),
        InlineKeyboardButton(text="RU Russkiy", callback_data="lang_ru"),
    ]])


def prem_kb(lang):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=TEXTS[lang]["buy"], callback_data="buy_premium"),
    ]])


@dp.message(Command("start"))
async def cmd_start(message: Message):
    get_user(message.from_user.id)["history"].clear()
    await message.answer("Choose language / Obery movu:", reply_markup=lang_kb())


@dp.callback_query(F.data.startswith("lang_"))
async def set_lang(callback: CallbackQuery):
    lang = callback.data.split("_")[1]
    get_user(callback.from_user.id)["lang"] = lang
    await callback.message.edit_text(TEXTS[lang]["welcome"])


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
    await message.answer(TEXTS[lang]["stats"].format(req=u["req"], status=status))


@dp.message(Command("premium"))
async def cmd_premium(message: Message):
    u = get_user(message.from_user.id)
    lang = u["lang"] or "ua"
    await message.answer(TEXTS[lang]["premium_info"], reply_markup=prem_kb(lang))


@dp.callback_query(F.data == "buy_premium")
async def buy_premium(callback: CallbackQuery):
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title="Premium",
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
    u["premium_until"] = date.today() + timedelta(days=30)
    await message.answer(TEXTS[lang]["premium_ok"])


@dp.message()
async def handle_message(message: Message):
    if not message.text:
        return
    u = get_user(message.from_user.id)
    if not u["lang"]:
        await message.answer("Choose language / Obery movu:", reply_markup=lang_kb())
        return
    lang = u["lang"]
    if not is_premium(u) and u["req"] >= FREE_LIMIT:
        await message.answer(TEXTS[lang]["limit"], reply_markup=prem_kb(lang))
        return
    u["history"].append({"role": "user", "content": message.text})
    thinking = await message.answer(TEXTS[lang]["thinking"])
    try:
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": "Ty korysnyy pomichnyk. Vidpovidai na movi korystuvacha."}] + u["history"][-20:],
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
    
