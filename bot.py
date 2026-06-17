import asyncio, logging, os
from groq import Groq
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
client = Groq(api_key=GROQ_API_KEY)
user_histories = {}

@dp.message(Command('start'))
async def start(m: Message): await m.answer('Привіт! Я ШІ-помічник. Напиши запитання!')

@dp.message(Command('clear'))
async def clear(m: Message):
    user_histories[m.from_user.id] = []
    await m.answer('Історію очищено!')

@dp.message()
async def handle(m: Message):
    if not m.text: return
    uid = m.from_user.id
    if uid not in user_histories: user_histories[uid] = []
    user_histories[uid].append({'role': 'user', 'content': m.text})
    t = await m.answer('Думаю...')
    try:
        r = await asyncio.to_thread(client.chat.completions.create, model='llama-3.3-70b-versatile', messages=[{'role': 'system', 'content': 'Ти корисний україномовний помічник.'}] + user_histories[uid])
        reply = r.choices[0].message.content
        user_histories[uid].append({'role': 'assistant', 'content': reply})
        await t.delete(); await m.answer(reply)
    except Exception as e:
        await t.delete(); await m.answer(str(e)[:300])

asyncio.run(dp.start_polling(bot))
