import asyncio
import base64
import os

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
client = OpenAI(api_key=OPENAI_API_KEY)

# =======================
# Состояния
# =======================

class CardState(StatesGroup):
    waiting_for_photo = State()
    waiting_for_holiday = State()
    waiting_for_phrase = State()

# =======================
# /start
# =======================

@dp.message(Command("start"))
async def start_handler(message: Message, state: FSMContext):
    await state.clear()

    text = (
        "Привет👋 Меня зовут Руслан и я помогу вам создать персональную открытку по вашей фотографии!\n\n"
        "Идея простая:\n"
        "Вы присылаете фото — я превращаю его в стильную праздничную открытку.\n\n"
        "К 8 марта💐\n"
        "Ко дню рождения🎉\n"
        "И к любому другому празднику.\n\n"
        "Присылай скорее фотографию того, кого хочешь поздравить!📷"
    )

    await message.answer_photo(
        photo="https://images.unsplash.com/photo-1511988617509-a57c8a288659",
        caption=text
    )

    await state.set_state(CardState.waiting_for_photo)

# =======================
# Получение фото
# =======================

@dp.message(CardState.waiting_for_photo, F.photo)
async def get_photo(message: Message, state: FSMContext):

    photo = message.photo[-1]
    await state.update_data(photo_file_id=photo.file_id)

    # Сообщение от бота (сохраняем id)
    msg = await message.answer(
        "Выбери праздник:"
    )

    await state.update_data(holiday_msg_id=msg.message_id)

    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="8 марта")],
            [KeyboardButton(text="День рождения")],
            [KeyboardButton(text="Другой праздник")]
        ],
        resize_keyboard=True
    )

    await message.answer(
        "Выбери праздник:",
        reply_markup=keyboard
    )

    await state.set_state(CardState.waiting_for_holiday)

# =======================
# Выбор праздника
# =======================

@dp.message(CardState.waiting_for_holiday)
async def choose_holiday(message: Message, state: FSMContext):

    data = await state.get_data()

    # Удаляем сообщение бота
    try:
        await bot.delete_message(
            message.chat.id,
            data["holiday_msg_id"]
        )
    except:
        pass

    await state.update_data(holiday=message.text)

    # Удаляем сообщение пользователя
    await message.delete()

    msg = await message.answer("Напиши фразу для открытки (до 100 символов):")

    await state.update_data(phrase_msg_id=msg.message_id)

    await state.set_state(CardState.waiting_for_phrase)

# =======================
# Генерация открытки
# =======================

@dp.message(CardState.waiting_for_phrase)
async def generate_card(message: Message, state: FSMContext):

    data = await state.get_data()

    phrase = message.text[:100]
    holiday = data["holiday"]

    # Удаляем подсказку бота
    try:
        await bot.delete_message(
            message.chat.id,
            data["phrase_msg_id"]
        )
    except:
        pass

    await message.delete()

    wait_msg = await message.answer("Создаю открытку ⏳")

    try:
        file = await bot.get_file(data["photo_file_id"])
        photo_bytes = await bot.download_file(file.file_path)
        photo_content = photo_bytes.read()

        prompt = f"""
Создай открытку из фото.

Праздник: {holiday}
Текст: {phrase}
Добавь надпись "С {holiday}"

Стиль:
Editorial illustration,
oil pastel texture,
chic fashion magazine style.

Формат 3:4
"""

        result = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size="1024x1536"
        )

        image_base64 = result.data[0].b64_json
        image_bytes = base64.b64decode(image_base64)

        await wait_msg.delete()

        await message.answer_photo(
            photo=image_bytes,
            caption="Готово 🎉"
        )

    except Exception as e:
        await wait_msg.edit_text("Ошибка генерации 😔")
        print(e)

    await state.clear()

# =======================

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
