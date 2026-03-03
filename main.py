import os
import asyncio
import base64

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove
)
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
client = OpenAI(api_key=OPENAI_API_KEY)

class PostcardState(StatesGroup):
    waiting_for_photo = State()
    waiting_for_holiday = State()
    waiting_for_phrase = State()

PROMPTS = {
    "8_march": """
Сделай открытку из этого фото. Сохрани черты лица и позу.
Открытка должна быть посвящена 8 марта с текстом [{phrase}] и [С 8 марта!].
Открытка сделана в стиле:
A bold editorial fashion illustration rendered in thick oil pastel or wax crayon,
with chunky, textured strokes on visible sketchbook paper. It should feel chic and modern, focusing on outfit and pose through expressive color blocks rather than outlines or realism. Формат 4:3
""",
    "birthday": """
Сделай открытку из этого фото. Сохрани черты лица и позу.
Открытка должна быть посвящена Дню рождения с текстом [{phrase}] и [С Днём рождения!].
Открытка сделана в стиле:
A bold editorial fashion illustration rendered in thick oil pastel or wax crayon,
with chunky, textured strokes on visible sketchbook paper. It should feel chic and modern, focusing on outfit and pose through expressive color blocks rather than outlines or realism. Формат 4:3
""",
    "23_feb": """
Сделай открытку из этого фото. Сохрани черты лица и позу.
Открытка должна быть посвящена 23 февраля с текстом [{phrase}] и [С Днем Защитника Отечества!].
Открытка сделана в стиле:
A bold editorial fashion illustration rendered in thick oil pastel or wax crayon,
with chunky, textured strokes on visible sketchbook paper. It should feel chic and modern, focusing on outfit and pose through expressive color blocks rather than outlines or realism. Формат 4:3
"""
}

@dp.message(F.text == "/start")
async def start(message: Message, state: FSMContext):
    await state.set_state(PostcardState.waiting_for_photo)
    await message.answer("Привет 👋 Отправь фото для открытки.")

@dp.message(PostcardState.waiting_for_photo, F.photo)
async def handle_photo(message: Message, state: FSMContext):
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    downloaded = await bot.download_file(file.file_path)

    await state.update_data(photo=downloaded.read())
    await state.set_state(PostcardState.waiting_for_holiday)

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="8 марта")],
            [KeyboardButton(text="День рождения")],
            [KeyboardButton(text="23 февраля")]
        ],
        resize_keyboard=True
    )

    await message.answer("Выбери праздник:", reply_markup=keyboard)

@dp.message(PostcardState.waiting_for_holiday)
async def choose_holiday(message: Message, state: FSMContext):

    holiday_map = {
        "8 марта": "8_march",
        "День рождения": "birthday",
        "23 февраля": "23_feb"
    }

    if message.text not in holiday_map:
        await message.answer("Выбери праздник кнопкой.")
        return

    await state.update_data(holiday=holiday_map[message.text])
    await state.set_state(PostcardState.waiting_for_phrase)

    await message.answer(
        "Напиши фразу для открытки (до 100 символов)",
        reply_markup=ReplyKeyboardRemove()
    )

@dp.message(PostcardState.waiting_for_phrase)
async def generate_postcard(message: Message, state: FSMContext):
    data = await state.get_data()

    phrase = message.text.strip()[:100]
    prompt_template = PROMPTS[data["holiday"]]
    prompt = prompt_template.format(phrase=phrase)

    await message.answer("Создаю открытку... ⏳")

    response = client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        image=data["photo"],
        size="1024x1536"
    )

    image_base64 = response.data[0].b64_json
    result = base64.b64decode(image_base64)

    await message.answer_photo(result)

    await state.clear()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
