import os
import asyncio
import sys
import json
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

print(f"✅ Python version: {sys.version}")

# ========== КОНФИГУРАЦИЯ ==========
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

if not TOKEN:
    print("❌ BOT_TOKEN не задан")
    sys.exit(1)

if not ADMIN_ID:
    print("⚠️ ADMIN_ID не задан, уведомления не будут отправляться")
    ADMIN_ID = None
else:
    ADMIN_ID = int(ADMIN_ID)

# ========== ИНИЦИАЛИЗАЦИЯ ==========
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Хранилище заявок
ORDERS_FILE = "orders.json"

def load_orders():
    try:
        with open(ORDERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_orders(orders):
    with open(ORDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(orders, f, indent=2, ensure_ascii=False)

# ========== СОСТОЯНИЯ ==========
class OrderForm(StatesGroup):
    name = State()
    contact = State()
    model_type = State()
    waiting_files = State()
    description = State()

# ========== КЛАВИАТУРЫ ==========
main_menu = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="📝 Оставить заявку")]],
    resize_keyboard=True
)

cancel_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="❌ Отмена")]],
    resize_keyboard=True
)

model_type_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="✅ У меня готовая модель")],
        [KeyboardButton(text="🎨 Нужно сделать модель в Blender")],
        [KeyboardButton(text="❌ Отмена")]
    ],
    resize_keyboard=True
)

# ========== КОМАНДЫ ==========
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "🏭 *Добро пожаловать в сервис 3D печати!*\n\n"
        "Я помогу оформить заказ на печать 3D моделей.\n\n"
        "📌 *Что я умею:*\n"
        "• Принимаю заявки на печать готовых моделей\n"
        "• Помогаю с созданием модели в Blender\n"
        "• Передам вашу заявку оператору\n\n"
        "Нажмите кнопку ниже, чтобы начать 👇",
        reply_markup=main_menu,
        parse_mode="Markdown"
    )

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "📖 *Помощь*\n\n"
        "📝 *Оставить заявку* - заполнить форму для заказа\n"
        "❌ *Отмена* - отменить текущую заявку\n"
        "/start - начать заново\n"
        "/status - проверить статус заявки\n\n"
        "По всем вопросам: @support",
        parse_mode="Markdown"
    )

@dp.message(Command("status"))
async def cmd_status(message: types.Message):
    orders = load_orders()
    user_id = str(message.from_user.id)
    
    if user_id in orders:
        order = orders[user_id]
        status_text = {
            "new": "⏳ На рассмотрении",
            "accepted": "✅ Принята",
            "rejected": "❌ Отклонена",
            "in_progress": "🔄 В работе"
        }.get(order.get("status", "new"), "❓ Неизвестно")
        
        await message.answer(
            f"📋 *Статус вашей заявки:* {status_text}\n\n"
            f"👤 Имя: {order['name']}\n"
            f"📞 Контакт: {order['contact']}\n\n"
            f"Оператор свяжется с вами в ближайшее время.",
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            "❌ У вас нет активных заявок.\n"
            "Хотите оставить новую? Нажмите 📝 Оставить заявку",
            reply_markup=main_menu
        )

# ========== ЗАЯВКА ==========
@dp.message(F.text == "📝 Оставить заявку")
async def start_order(message: types.Message, state: FSMContext):
    await state.set_state(OrderForm.name)
    await message.answer(
        "🔹 *Как вас зовут?*\n\n"
        "Напишите ваше имя:",
        reply_markup=cancel_kb,
        parse_mode="Markdown"
    )

@dp.message(F.text == "❌ Отмена")
async def cancel_order(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "❌ Заявка отменена.\n\n"
        "Если передумаете, нажмите 📝 Оставить заявку",
        reply_markup=main_menu
    )

@dp.message(OrderForm.name)
async def get_name(message: types.Message, state: FSMContext):
    if len(message.text) < 2:
        await message.answer("❌ Пожалуйста, введите корректное имя (минимум 2 символа)")
        return
    
    await state.update_data(name=message.text)
    await state.set_state(OrderForm.contact)
    await message.answer(
        "🔹 *Где вам удобно связаться?*\n\n"
        "📱 Номер телефона\n"
        "📧 Email\n"
        "Или напишите 'пропустить' - буду писать сюда в Telegram\n\n"
        "Введите контактные данные:",
        reply_markup=cancel_kb,
        parse_mode="Markdown"
    )

@dp.message(OrderForm.contact)
async def get_contact(message: types.Message, state: FSMContext):
    contact = message.text.strip()
    if not contact or contact.lower() == "пропустить":
        username = message.from_user.username
        if username:
            contact = f"Telegram: @{username}"
        else:
            contact = f"Telegram ID: {message.from_user.id}"
    
    await state.update_data(contact=contact)
    await state.set_state(OrderForm.model_type)
    await message.answer(
        "🔹 *У вас есть готовая модель?*\n\n"
        "Выберите подходящий вариант:",
        reply_markup=model_type_kb,
        parse_mode="Markdown"
    )

@dp.message(OrderForm.model_type)
async def get_model_type(message: types.Message, state: FSMContext):
    if "готовая модель" in message.text:
        await state.update_data(model_type="ready", files=[])
        await state.set_state(OrderForm.waiting_files)
        await message.answer(
            "📁 *Отправьте файл модели*\n\n"
            "Поддерживаемые форматы: STL, OBJ, 3MF\n\n"
            "📌 Можно отправить несколько файлов.\n"
            "Когда закончите, напишите *готово*",
            reply_markup=cancel_kb,
            parse_mode="Markdown"
        )
    elif "сделать модель" in message.text or "Blender" in message.text:
        await state.update_data(model_type="need_design", files=[])
        await state.set_state(OrderForm.description)
        await message.answer(
            "🎨 *Опишите, что нужно смоделировать*\n\n"
            "Укажите:\n"
            "• Назначение детали\n"
            "• Примерные размеры\n"
            "• Особенности формы\n\n"
            "Чем подробнее описание, тем точнее будет результат!",
            reply_markup=cancel_kb,
            parse_mode="Markdown"
        )
    else:
        await message.answer("❌ Пожалуйста, выберите вариант из кнопок меню")

@dp.message(OrderForm.waiting_files)
async def get_files(message: types.Message, state: FSMContext):
    data = await state.get_data()
    files = data.get("files", [])
    
    if message.document:
        file_name = message.document.file_name
        ext = file_name.split('.')[-1].lower() if '.' in file_name else ''
        
        if ext not in ['stl', 'obj', '3mf', 'step']:
            await message.answer(
                "❌ Неподдерживаемый формат файла.\n"
                "Отправьте файлы в формате: STL, OBJ, 3MF"
            )
            return
        
        files.append({
            "file_id": message.document.file_id,
            "name": file_name
        })
        await state.update_data(files=files)
        await message.answer(
            f"✅ Файл *{file_name}* добавлен.\n"
            f"Всего файлов: {len(files)}\n\n"
            "Можете отправить еще или напишите *готово*",
            parse_mode="Markdown"
        )
    
    elif message.text and message.text.lower() == "готово":
        if not files:
            await message.answer(
                "❌ Вы не отправили ни одного файла.\n"
                "Пожалуйста, отправьте хотя бы один файл модели"
            )
            return
        
        await state.set_state(OrderForm.description)
        await message.answer(
            "📝 *Опишите пожелания по печати:*\n\n"
            "• Материал (PLA, ABS, PETG, смола)\n"
            "• Цвет\n"
            "• Качество печати\n"
            "• Сроки\n\n"
            "Напишите все, что считаете важным:",
            reply_markup=cancel_kb,
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            "📁 Отправьте файл модели или напишите *готово*",
            reply_markup=cancel_kb
        )

@dp.message(OrderForm.description)
async def get_description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    
    user_data = await state.get_data()
    user_id = message.from_user.id
    
    order = {
        "user_id": user_id,
        "username": message.from_user.username,
        "full_name": message.from_user.full_name,
        "name": user_data["name"],
        "contact": user_data["contact"],
        "model_type": user_data["model_type"],
        "files": user_data.get("files", []),
        "description": user_data["description"],
        "status": "new",
        "created_at": str(message.date)
    }
    
    orders = load_orders()
    orders[str(user_id)] = order
    save_orders(orders)
    
    await message.answer(
        "✅ *Заявка успешно отправлена!*\n\n"
        "Я передал её оператору.\n"
        "Статус заявки можно проверить командой /status",
        reply_markup=main_menu,
        parse_mode="Markdown"
    )
    
    if ADMIN_ID:
        await notify_admin(order, user_id)
    
    await state.clear()

# ========== УВЕДОМЛЕНИЕ АДМИНУ ==========
async def notify_admin(order: dict, user_id: int):
    model_type_text = "✅ Готовая модель" if order["model_type"] == "ready" else "🎨 Требуется дизайн в Blender"
    
    text = (
        f"🔔 *НОВАЯ ЗАЯВКА!*\n"
        f"{'='*30}\n\n"
        f"👤 *Клиент:* {order['name']}\n"
        f"🆔 *Telegram ID:* {user_id}\n"
        f"📱 *Username:* @{order['username'] or 'Нет'}\n"
        f"📞 *Контакт:* {order['contact']}\n\n"
        f"🖨️ *Тип:* {model_type_text}\n\n"
        f"📝 *Пожелания:*\n{order['description']}\n"
    )
    
    if order["files"]:
        text += f"\n📁 *Файлов:* {len(order['files'])} шт.\n"
    
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="💬 Написать клиенту", url=f"tg://user?id={user_id}")],
        [types.InlineKeyboardButton(text="✅ Принять", callback_data=f"accept_{user_id}"),
         types.InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{user_id}")]
    ])
    
    await bot.send_message(ADMIN_ID, text, parse_mode="Markdown", reply_markup=kb)
    
    if order["files"]:
        await bot.send_message(ADMIN_ID, "📎 *Файлы модели:*", parse_mode="Markdown")
        for file in order["files"]:
            await bot.send_document(ADMIN_ID, file["file_id"], caption=file["name"])

# ========== ДЕЙСТВИЯ АДМИНА ==========
@dp.callback_query()
async def handle_admin_actions(callback: types.CallbackQuery):
    if ADMIN_ID and callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Эта кнопка только для администратора", show_alert=True)
        return
    
    action, user_id = callback.data.split("_")
    user_id = int(user_id)
    orders = load_orders()
    
    if action == "accept":
        if str(user_id) in orders:
            orders[str(user_id)]["status"] = "accepted"
            save_orders(orders)
            
            await bot.send_message(
                user_id,
                "✅ *Ваша заявка принята!*\n\n"
                "Скоро с вами свяжется оператор.",
                parse_mode="Markdown"
            )
            
            await callback.message.edit_text(
                callback.message.text + "\n\n✅ ЗАЯВКА ПРИНЯТА"
            )
            await callback.answer("✅ Заявка принята")
    
    elif action == "reject":
        if str(user_id) in orders:
            orders[str(user_id)]["status"] = "rejected"
            save_orders(orders)
            
            await bot.send_message(
                user_id,
                "❌ *Ваша заявка отклонена.*\n\n"
                "Вы можете оставить новую заявку через /start",
                parse_mode="Markdown"
            )
            
            await callback.message.edit_text(
                callback.message.text + "\n\n❌ ЗАЯВКА ОТКЛОНЕНА"
            )
            await callback.answer("❌ Заявка отклонена")

# ========== ЗАПУСК ==========
async def main():
    print("🚀 Бот запускается...")
    print(f"🤖 Bot token: {TOKEN[:10]}...")
    print(f"👑 Admin ID: {ADMIN_ID}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
