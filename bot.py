import asyncio
import logging
import os
from groq import Groq
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
client = Groq(api_key=GROQ_API_KEY)
user_histories = {}


@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("Pryvit! Ya ShI-pomichnyk. Napyshy bud-yake zapytannya!")


@dp.message(Command("clear"))
async def cmd_clear(message: Message):
    user_histories[message.from_user.id] = []
    await message.answer("Istoriyu ochyshcheno!")


@dp.message()
async def handle_message(message: Message):
    if not message.text:
        return
    uid = message.from_user.id
    if uid not in user_histories:
        user_histories[uid] = []
    user_histories[uid].append({"role": "user", "content": message.text})
    thinking = await message.answer("Dumayu...")
    try:
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": "Ty korysnyy pomichnyk. Vidpovidai na movi korystuvacha."}] + user_histories[uid][-20:]
        )
        reply = response.choices[0].message.content
        user_histories[uid].append({"role": "assistant", "content": reply})
        await thinking.delete()
        await message.answer(reply)
    except Exception as e:
        await thinking.delete()
        await message.answer(str(e)[:300])


async def main():
    print("Bot started!")
    await dp.start_polling(bot)


if name == "main":
    asyncio.run(main())
