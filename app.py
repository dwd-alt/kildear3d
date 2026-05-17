import os
import asyncio
import sys
import json
import random
import string
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

print(f"✅ Python version: {sys.version}")

# ========== КОНФИГУРАЦИЯ ==========
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

if not TOKEN:
    print("❌ BOT_TOKEN не задан")
    sys.exit(1)

if not ADMIN_ID:
    print("⚠️ ADMIN_ID не задан")
    ADMIN_ID = None
else:
    ADMIN_ID = int(ADMIN_ID)

# ========== ИНИЦИАЛИЗАЦИЯ БОТА ==========
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ========== ЮРИДИЧЕСКИЙ ТЕКСТ ==========
LEGAL_TEXT = """
📜 *ПРАВИЛА И УСЛОВИЯ 3D ПЕЧАТИ*

🔹 *Оплата:*
• 100% предоплата перед началом печати
• Стоимость рассчитывается после получения модели

🔹 *Ответственность за модель:*
• Клиент предоставляет готовую модель (STL/OBJ/3MF)
• Исполнитель НЕ гарантирует качество печати, если модель имеет ошибки

🔹 *Доставка:*
• Самовывоз
• Отправка Почтой / СДЭК (за счет клиента)
"""

# ========== ХРАНИЛИЩА ==========
ORDERS_FILE = "orders.json"
PARTNERS_FILE = "partners.json"
DESIGNERS_FILE = "designers.json"
FRANCHISE_FILE = "franchise.json"
PROMOCODES_FILE = "promocodes.json"

def load_json(file):
    try:
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def generate_promo():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

# ========== СОСТОЯНИЯ ==========
class OrderForm(StatesGroup):
    legal_accept = State()
    name = State()
    contact = State()
    delivery = State()
    promo = State()
    model_type = State()
    waiting_files = State()
    description = State()

class PartnerReg(StatesGroup):
    name = State()
    contact = State()
    reward_type = State()
    payment_info = State()

class DesignerReg(StatesGroup):
    name = State()
    experience = State()
    skills = State()
    portfolio = State()

class FranchiseReg(StatesGroup):
    name = State()
    city = State()
    printer_model = State()
    contact = State()

# ========== КЛАВИАТУРЫ ==========
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📝 Оставить заявку")],
        [KeyboardButton(text="🤝 Стать партнером"), KeyboardButton(text="🎨 Стать дизайнером")],
        [KeyboardButton(text="🏭 Стать частью фирмы"), KeyboardButton(text="📜 Правила")]
    ],
    resize_keyboard=True
)

cancel_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="❌ Отмена")]],
    resize_keyboard=True
)

reward_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💰 Процент деньгами")],
        [KeyboardButton(text="🎁 Скидка на печать")],
        [KeyboardButton(text="❌ Отмена")]
    ],
    resize_keyboard=True
)

delivery_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🚗 Самовывоз")],
        [KeyboardButton(text="📦 Почта")],
        [KeyboardButton(text="🚚 СДЭК")],
        [KeyboardButton(text="❌ Отмена")]
    ],
    resize_keyboard=True
)

model_type_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="✅ Готовая модель")],
        [KeyboardButton(text="🎨 Нужен дизайн")],
        [KeyboardButton(text="❌ Отмена")]
    ],
    resize_keyboard=True
)

# ========== КОМАНДЫ ==========
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "🏭 *ИП «Kildear» - 3D печать*\n\n"
        "Выберите действие:",
        reply_markup=main_menu,
        parse_mode="Markdown"
    )

@dp.message(Command("rules"))
async def cmd_rules(message: types.Message):
    await message.answer(LEGAL_TEXT, parse_mode="Markdown")

@dp.message(F.text == "📜 Правила")
async def rules_button(message: types.Message):
    await message.answer(LEGAL_TEXT, parse_mode="Markdown")

# ========== ОТДЕЛ 1: ПАРТНЕРЫ ==========
@dp.message(F.text == "🤝 Стать партнером")
async def start_partner_reg(message: types.Message, state: FSMContext):
    await state.set_state(PartnerReg.name)
    await message.answer(
        "🤝 *Регистрация в партнерской программе*\n\nКак вас зовут?",
        reply_markup=cancel_kb,
        parse_mode="Markdown"
    )

@dp.message(PartnerReg.name)
async def partner_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(PartnerReg.contact)
    await message.answer("📱 *Контакты для связи* (телефон / Telegram):", parse_mode="Markdown")

@dp.message(PartnerReg.contact)
async def partner_contact(message: types.Message, state: FSMContext):
    await state.update_data(contact=message.text)
    await state.set_state(PartnerReg.reward_type)
    await message.answer(
        "🎁 *Как хотите получать вознаграждение?*",
        reply_markup=reward_kb,
        parse_mode="Markdown"
    )

@dp.message(PartnerReg.reward_type)
async def partner_reward_type(message: types.Message, state: FSMContext):
    if "деньгами" in message.text:
        await state.update_data(reward_type="money")
        await state.set_state(PartnerReg.payment_info)
        await message.answer("💳 *Укажите реквизиты для перевода* (номер карты или телефона):", parse_mode="Markdown")
    elif "скидка" in message.text:
        await state.update_data(reward_type="discount")
        await complete_partner_reg(message, state)
    else:
        await message.answer("Выберите вариант из кнопок")

@dp.message(PartnerReg.payment_info)
async def partner_payment(message: types.Message, state: FSMContext):
    await state.update_data(payment_info=message.text)
    await complete_partner_reg(message, state)

async def complete_partner_reg(message: types.Message, state: FSMContext):
    data = await state.get_data()
    promo = generate_promo()
    
    partner = {
        "user_id": message.from_user.id,
        "username": message.from_user.username,
        "name": data["name"],
        "contact": data["contact"],
        "reward_type": data["reward_type"],
        "payment_info": data.get("payment_info", ""),
        "promocode": promo,
        "balance": 0,
        "created_at": str(datetime.now())
    }
    
    partners = load_json(PARTNERS_FILE)
    partners[str(message.from_user.id)] = partner
    save_json(PARTNERS_FILE, partners)
    
    promocodes = load_json(PROMOCODES_FILE)
    promocodes[promo] = {"partner_id": message.from_user.id, "used": False, "used_by": None}
    save_json(PROMOCODES_FILE, promocodes)
    
    await message.answer(
        f"✅ *Вы зарегистрированы в партнерской программе!*\n\n"
        f"🤝 Ваш промокод: *{promo}*\n\n"
        f"📌 Дайте промокод клиентам, они получат скидку 10%, а вы - 10% от заказа.",
        reply_markup=main_menu,
        parse_mode="Markdown"
    )
    
    if ADMIN_ID:
        await bot.send_message(
            ADMIN_ID,
            f"🔔 *Новый партнер!*\n👤 {data['name']}\n📞 {data['contact']}\n🎟 Промокод: {promo}",
            parse_mode="Markdown"
        )
    await state.clear()

# ========== ОТДЕЛ 2: ДИЗАЙНЕРЫ ==========
@dp.message(F.text == "🎨 Стать дизайнером")
async def start_designer_reg(message: types.Message, state: FSMContext):
    await state.set_state(DesignerReg.name)
    await message.answer(
        "🎨 *Регистрация 3D дизайнера*\n\nКак вас зовут?",
        reply_markup=cancel_kb,
        parse_mode="Markdown"
    )

@dp.message(DesignerReg.name)
async def designer_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(DesignerReg.experience)
    await message.answer("⏱ *Стаж работы* (в годах):", parse_mode="Markdown")

@dp.message(DesignerReg.experience)
async def designer_experience(message: types.Message, state: FSMContext):
    await state.update_data(experience=message.text)
    await state.set_state(DesignerReg.skills)
    await message.answer("🛠 *В каких программах работаете?* (Blender, Fusion360, SolidWorks):", parse_mode="Markdown")

@dp.message(DesignerReg.skills)
async def designer_skills(message: types.Message, state: FSMContext):
    await state.update_data(skills=message.text)
    await state.set_state(DesignerReg.portfolio)
    await message.answer("📎 *Ссылка на портфолио* (Google Drive, Behance, Instagram):", parse_mode="Markdown")

@dp.message(DesignerReg.portfolio)
async def designer_portfolio(message: types.Message, state: FSMContext):
    data = await state.get_data()
    
    designer = {
        "user_id": message.from_user.id,
        "username": message.from_user.username,
        "name": data["name"],
        "experience": data["experience"],
        "skills": data["skills"],
        "portfolio": message.text,
        "status": "pending",
        "created_at": str(datetime.now())
    }
    
    designers = load_json(DESIGNERS_FILE)
    designers[str(message.from_user.id)] = designer
    save_json(DESIGNERS_FILE, designers)
    
    await message.answer(
        "✅ *Заявка отправлена!*\n\nЕсли одобрят — с вами свяжутся.",
        reply_markup=main_menu,
        parse_mode="Markdown"
    )
    
    if ADMIN_ID:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Принять", callback_data=f"accept_designer_{message.from_user.id}"),
             InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_designer_{message.from_user.id}")]
        ])
        await bot.send_message(
            ADMIN_ID,
            f"🔔 *Новая заявка дизайнера!*\n👤 {data['name']}\n⏱ Стаж: {data['experience']} лет\n🛠 {data['skills']}\n📎 {message.text}",
            parse_mode="Markdown",
            reply_markup=kb
        )
    await state.clear()

# ========== ОТДЕЛ 3: ФИЛИАЛЫ ==========
@dp.message(F.text == "🏭 Стать частью фирмы")
async def start_franchise_reg(message: types.Message, state: FSMContext):
    await state.set_state(FranchiseReg.name)
    await message.answer(
        "🏭 *Регистрация филиала*\n\nКак вас зовут?",
        reply_markup=cancel_kb,
        parse_mode="Markdown"
    )

@dp.message(FranchiseReg.name)
async def franchise_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(FranchiseReg.city)
    await message.answer("📍 *Из какого вы города?*", parse_mode="Markdown")

@dp.message(FranchiseReg.city)
async def franchise_city(message: types.Message, state: FSMContext):
    await state.update_data(city=message.text)
    await state.set_state(FranchiseReg.printer_model)
    await message.answer("🖨️ *Какая модель 3D принтера?*", parse_mode="Markdown")

@dp.message(FranchiseReg.printer_model)
async def franchise_printer(message: types.Message, state: FSMContext):
    await state.update_data(printer_model=message.text)
    await state.set_state(FranchiseReg.contact)
    await message.answer("📞 *Контакты для связи* (телефон / Telegram):", parse_mode="Markdown")

@dp.message(FranchiseReg.contact)
async def franchise_contact(message: types.Message, state: FSMContext):
    data = await state.get_data()
    
    franchise = {
        "user_id": message.from_user.id,
        "username": message.from_user.username,
        "name": data["name"],
        "city": data["city"],
        "printer_model": data["printer_model"],
        "contact": message.text,
        "status": "pending",
        "created_at": str(datetime.now())
    }
    
    franchises = load_json(FRANCHISE_FILE)
    franchises[str(message.from_user.id)] = franchise
    save_json(FRANCHISE_FILE, franchises)
    
    await message.answer(
        "✅ *Заявка отправлена!*\n\nЕсли одобрят — вы станете частью фирмы (80% вам, 20% нам).",
        reply_markup=main_menu,
        parse_mode="Markdown"
    )
    
    if ADMIN_ID:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Одобрить", callback_data=f"accept_franchise_{message.from_user.id}"),
             InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_franchise_{message.from_user.id}")]
        ])
        await bot.send_message(
            ADMIN_ID,
            f"🔔 *Новый филиал!*\n👤 {data['name']}\n📍 {data['city']}\n🖨 {data['printer_model']}\n📞 {message.text}",
            parse_mode="Markdown",
            reply_markup=kb
        )
    await state.clear()

# ========== ОБРАБОТКА ЗАЯВОК АДМИНА ==========
@dp.callback_query(lambda c: c.data.startswith(("accept_designer_", "reject_designer_", "accept_franchise_", "reject_franchise_")))
async def handle_admin_approvals(callback: types.CallbackQuery):
    if ADMIN_ID and callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Только для админа", show_alert=True)
        return
    
    parts = callback.data.split("_")
    action = parts[0]
    role = parts[1]
    user_id = int(parts[2])
    
    if role == "designer":
        designers = load_json(DESIGNERS_FILE)
        if str(user_id) in designers:
            if action == "accept":
                designers[str(user_id)]["status"] = "accepted"
                save_json(DESIGNERS_FILE, designers)
                await bot.send_message(user_id, "✅ *Заявка дизайнера одобрена!* С вами свяжутся.", parse_mode="Markdown")
            else:
                designers[str(user_id)]["status"] = "rejected"
                save_json(DESIGNERS_FILE, designers)
                await bot.send_message(user_id, "❌ Заявка отклонена.", parse_mode="Markdown")
            await callback.message.edit_text(callback.message.text + f"\n\n✅ {action.upper()}")
    
    elif role == "franchise":
        franchises = load_json(FRANCHISE_FILE)
        if str(user_id) in franchises:
            if action == "accept":
                franchises[str(user_id)]["status"] = "accepted"
                save_json(FRANCHISE_FILE, franchises)
                await bot.send_message(user_id, "✅ *Вы стали частью фирмы!* 80% вам, 20% нам.", parse_mode="Markdown")
            else:
                franchises[str(user_id)]["status"] = "rejected"
                save_json(FRANCHISE_FILE, franchises)
                await bot.send_message(user_id, "❌ Заявка отклонена.", parse_mode="Markdown")
            await callback.message.edit_text(callback.message.text + f"\n\n✅ {action.upper()}")
    
    await callback.answer()

# ========== ОСНОВНАЯ ЗАЯВКА (упрощенно для теста) ==========
@dp.message(F.text == "📝 Оставить заявку")
async def start_order(message: types.Message):
    await message.answer(
        "📝 *Форма заявки*\n\n"
        "Для оформления заказа напишите:\n"
        "• Ваше имя\n"
        "• Контакт\n"
        "• Описание модели\n\n"
        "Или свяжитесь с оператором напрямую.",
        reply_markup=main_menu,
        parse_mode="Markdown"
    )

@dp.message(F.text == "❌ Отмена")
async def cancel_action(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Действие отменено.", reply_markup=main_menu)

# ========== ЗАПУСК ==========
async def main():
    print("🚀 Бот ИП «Kildear» запущен!")
    print(f"✅ Токен: {TOKEN[:10]}...")
    print(f"✅ ADMIN_ID: {ADMIN_ID}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
