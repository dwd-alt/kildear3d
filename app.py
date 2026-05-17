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

# ========== ЮРИДИЧЕСКИЙ ТЕКСТ (старое соглашение) ==========
LEGAL_TEXT = """
📜 *ПРАВИЛА И УСЛОВИЯ 3D ПЕЧАТИ*

🔹 *Оплата:*
• 100% предоплата перед началом печати
• Стоимость рассчитывается после получения модели и согласования параметров
• Оплата принимается на карту или через СБП

🔹 *Ответственность за модель:*
• Клиент предоставляет готовую модель (STL/OBJ/3MF)
• Исполнитель НЕ гарантирует качество печати, если модель имеет геометрические ошибки, негерметичность или не соответствует техническим требованиям
• Рекомендуется проверять модель перед отправкой (программы: Netfabb, Meshmixer)

🔹 *Гарантии:*
• При нарушении геометрии модели — перепечатка за счет клиента
• При технической ошибке исполнителя — перепечатка за наш счет
• Цвет и материал могут незначительно отличаться от ожидаемых

🔹 *Сроки:*
• Обсуждаются индивидуально после подтверждения заявки
• Срочные заказы — с наценкой 30%

🔹 *Доставка:*
• Самовывоз (адрес сообщу после оплаты)
• Отправка Почтой России / СДЭК (за счет клиента)

🔹 *Отказ от ответственности:*
• Исполнитель не несет ответственности за использование напечатанной детали не по назначению
• Функциональность модели зависит от качества предоставленного файла
• Результат печати может отличаться от ожидаемого клиентом

Нажимая \"✅ Принимаю условия\", вы подтверждаете согласие с данными правилами.
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
        [KeyboardButton(text="📦 Почта России")],
        [KeyboardButton(text="🚚 СДЭК")],
        [KeyboardButton(text="❌ Отмена")]
    ],
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

# ========== ОСНОВНАЯ ЗАЯВКА (полная версия) ==========
@dp.message(F.text == "📝 Оставить заявку")
async def start_order(message: types.Message, state: FSMContext):
    await state.set_state(OrderForm.legal_accept)
    await message.answer(
        LEGAL_TEXT + "\n\n⬇️ *Для продолжения примите условия* ⬇️",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Принимаю условия", callback_data="accept_legal")]
        ])
    )

@dp.callback_query(lambda c: c.data == "accept_legal")
async def handle_legal(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("✅ *Условия приняты!* Продолжаем оформление заявки.", parse_mode="Markdown")
    await state.set_state(OrderForm.name)
    await callback.message.answer(
        "🔹 *Как вас зовут?*\n\nНапишите ваше имя:",
        reply_markup=cancel_kb,
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.message(F.text == "❌ Отмена")
async def cancel_order(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "❌ Заявка отменена.\n\nЕсли передумаете, нажмите 📝 Оставить заявку",
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
    await state.set_state(OrderForm.delivery)
    await message.answer(
        "🔹 *Как получить готовый заказ?*\n\nВыберите способ получения:",
        reply_markup=delivery_kb,
        parse_mode="Markdown"
    )

@dp.message(OrderForm.delivery)
async def get_delivery(message: types.Message, state: FSMContext):
    if "Самовывоз" in message.text:
        delivery = "🚗 Самовывоз (адрес сообщу после оплаты)"
    elif "Почта" in message.text:
        delivery = "📦 Отправка Почтой России (доставка за счет клиента)"
    elif "СДЭК" in message.text:
        delivery = "🚚 Отправка СДЭК (доставка за счет клиента)"
    else:
        await message.answer("❌ Пожалуйста, выберите способ получения из кнопок")
        return
    
    await state.update_data(delivery=delivery)
    await state.set_state(OrderForm.promo)
    await message.answer(
        "🎟 *Есть промокод?*\n\nВведите промокод или напишите 'пропустить':",
        reply_markup=cancel_kb,
        parse_mode="Markdown"
    )

@dp.message(OrderForm.promo)
async def get_promo(message: types.Message, state: FSMContext):
    promo = None if message.text.lower() == "пропустить" else message.text.upper()
    if promo:
        promocodes = load_json(PROMOCODES_FILE)
        if promo in promocodes and not promocodes[promo]["used"]:
            await state.update_data(promo=promo)
            await message.answer(f"✅ Промокод *{promo}* активирован! Вы получите скидку 10% после оплаты.", parse_mode="Markdown")
        else:
            await message.answer("❌ Неверный или уже использованный промокод. Продолжаем без скидки.")
            await state.update_data(promo=None)
    else:
        await state.update_data(promo=None)
    
    await state.set_state(OrderForm.model_type)
    await message.answer(
        "🔹 *У вас есть готовая модель?*\n\nВыберите вариант:",
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
            "⚠️ *Важно:* Перед отправкой проверьте модель на ошибки!\n"
            "Исполнитель не гарантирует качество печати при геометрических ошибках.\n\n"
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
            "• Особенности формы\n"
            "• Ссылки на референсы (если есть)\n\n"
            "Чем подробнее описание, тем точнее будет результат!\n\n"
            "💰 Стоимость дизайна обсуждается индивидуально.",
            reply_markup=cancel_kb,
            parse_mode="Markdown"
        )
    else:
        await message.answer("❌ Пожалуйста, выберите вариант из кнопок")

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
            "• Качество печати (черновая/стандартная/высокая)\n"
            "• Сроки\n"
            "• Особые требования\n\n"
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
    promo = user_data.get("promo")
    
    order = {
        "user_id": user_id,
        "username": message.from_user.username,
        "full_name": message.from_user.full_name,
        "name": user_data["name"],
        "contact": user_data["contact"],
        "delivery": user_data["delivery"],
        "promocode": promo,
        "model_type": user_data["model_type"],
        "files": user_data.get("files", []),
        "description": user_data["description"],
        "status": "new",
        "legal_accepted": True,
        "created_at": str(datetime.now())
    }
    
    orders = load_json(ORDERS_FILE)
    orders[str(user_id)] = order
    save_json(ORDERS_FILE, orders)
    
    await message.answer(
        "✅ *Заявка успешно отправлена!*\n\n"
        "Я передал её оператору.\n"
        "Статус заявки можно проверить командой /status\n\n"
        "📜 Напоминаем: работа начинается только после 100% предоплаты.",
        reply_markup=main_menu,
        parse_mode="Markdown"
    )
    
    if ADMIN_ID:
        await notify_admin(order, user_id)
    
    await state.clear()

async def notify_admin(order: dict, user_id: int):
    model_type_text = "✅ Готовая модель" if order["model_type"] == "ready" else "🎨 Требуется дизайн в Blender"
    
    text = (
        f"🔔 *НОВАЯ ЗАЯВКА!*\n"
        f"{'='*30}\n\n"
        f"👤 *Клиент:* {order['name']}\n"
        f"🆔 *Telegram ID:* {user_id}\n"
        f"📱 *Username:* @{order['username'] or 'Нет'}\n"
        f"📞 *Контакт:* {order['contact']}\n"
        f"🚚 *Доставка:* {order['delivery']}\n\n"
        f"🖨️ *Тип:* {model_type_text}\n\n"
        f"📝 *Пожелания:*\n{order['description']}\n"
    )
    
    if order.get("promocode"):
        text += f"\n🎟 *Промокод:* {order['promocode']}\n"
    
    if order["files"]:
        text += f"\n📁 *Файлов:* {len(order['files'])} шт.\n"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Написать клиенту", url=f"tg://user?id={user_id}")],
        [InlineKeyboardButton(text="✅ Принять", callback_data=f"accept_order_{user_id}"),
         InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_order_{user_id}")]
    ])
    
    await bot.send_message(ADMIN_ID, text, parse_mode="Markdown", reply_markup=kb)
    
    if order["files"]:
        for file in order["files"]:
            await bot.send_document(ADMIN_ID, file["file_id"], caption=file["name"])

# ========== ОБРАБОТКА ЗАЯВОК АДМИНА ==========
@dp.callback_query(lambda c: c.data.startswith(("accept_designer_", "reject_designer_", "accept_franchise_", "reject_franchise_", "accept_order_", "reject_order_")))
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
    
    elif role == "order":
        orders = load_json(ORDERS_FILE)
        if str(user_id) in orders:
            if action == "accept":
                orders[str(user_id)]["status"] = "accepted"
                save_json(ORDERS_FILE, orders)
                await bot.send_message(user_id, "✅ *Ваша заявка принята!* Скоро свяжемся.", parse_mode="Markdown")
            else:
                orders[str(user_id)]["status"] = "rejected"
                save_json(ORDERS_FILE, orders)
                await bot.send_message(user_id, "❌ Заявка отклонена.", parse_mode="Markdown")
            await callback.message.edit_text(callback.message.text + f"\n\n✅ {action.upper()}")
    
    await callback.answer()

@dp.message(Command("status"))
async def cmd_status(message: types.Message):
    orders = load_json(ORDERS_FILE)
    user_id = str(message.from_user.id)
    
    if user_id in orders:
        order = orders[user_id]
        status_text = {
            "new": "⏳ На рассмотрении",
            "accepted": "✅ Принята",
            "rejected": "❌ Отклонена"
        }.get(order.get("status", "new"), "❓ Неизвестно")
        
        await message.answer(
            f"📋 *Статус вашей заявки:* {status_text}\n\n"
            f"👤 Имя: {order['name']}\n"
            f"📞 Контакт: {order['contact']}\n"
            f"🚚 Доставка: {order.get('delivery', 'Не указана')}",
            parse_mode="Markdown"
        )
    else:
        await message.answer("❌ У вас нет активных заявок.", reply_markup=main_menu)

# ========== ЗАПУСК ==========
async def main():
    print("🚀 Бот ИП «Kildear» запущен!")
    print(f"✅ Токен: {TOKEN[:10]}...")
    print(f"✅ ADMIN_ID: {ADMIN_ID}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())import os
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

# ========== ЮРИДИЧЕСКИЙ ТЕКСТ (старое соглашение) ==========
LEGAL_TEXT = """
📜 *ПРАВИЛА И УСЛОВИЯ 3D ПЕЧАТИ*

🔹 *Оплата:*
• 100% предоплата перед началом печати
• Стоимость рассчитывается после получения модели и согласования параметров
• Оплата принимается на карту или через СБП

🔹 *Ответственность за модель:*
• Клиент предоставляет готовую модель (STL/OBJ/3MF)
• Исполнитель НЕ гарантирует качество печати, если модель имеет геометрические ошибки, негерметичность или не соответствует техническим требованиям
• Рекомендуется проверять модель перед отправкой (программы: Netfabb, Meshmixer)

🔹 *Гарантии:*
• При нарушении геометрии модели — перепечатка за счет клиента
• При технической ошибке исполнителя — перепечатка за наш счет
• Цвет и материал могут незначительно отличаться от ожидаемых

🔹 *Сроки:*
• Обсуждаются индивидуально после подтверждения заявки
• Срочные заказы — с наценкой 30%

🔹 *Доставка:*
• Самовывоз (адрес сообщу после оплаты)
• Отправка Почтой России / СДЭК (за счет клиента)

🔹 *Отказ от ответственности:*
• Исполнитель не несет ответственности за использование напечатанной детали не по назначению
• Функциональность модели зависит от качества предоставленного файла
• Результат печати может отличаться от ожидаемого клиентом

Нажимая \"✅ Принимаю условия\", вы подтверждаете согласие с данными правилами.
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
        [KeyboardButton(text="📦 Почта России")],
        [KeyboardButton(text="🚚 СДЭК")],
        [KeyboardButton(text="❌ Отмена")]
    ],
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

# ========== ОСНОВНАЯ ЗАЯВКА (полная версия) ==========
@dp.message(F.text == "📝 Оставить заявку")
async def start_order(message: types.Message, state: FSMContext):
    await state.set_state(OrderForm.legal_accept)
    await message.answer(
        LEGAL_TEXT + "\n\n⬇️ *Для продолжения примите условия* ⬇️",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Принимаю условия", callback_data="accept_legal")]
        ])
    )

@dp.callback_query(lambda c: c.data == "accept_legal")
async def handle_legal(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("✅ *Условия приняты!* Продолжаем оформление заявки.", parse_mode="Markdown")
    await state.set_state(OrderForm.name)
    await callback.message.answer(
        "🔹 *Как вас зовут?*\n\nНапишите ваше имя:",
        reply_markup=cancel_kb,
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.message(F.text == "❌ Отмена")
async def cancel_order(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "❌ Заявка отменена.\n\nЕсли передумаете, нажмите 📝 Оставить заявку",
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
    await state.set_state(OrderForm.delivery)
    await message.answer(
        "🔹 *Как получить готовый заказ?*\n\nВыберите способ получения:",
        reply_markup=delivery_kb,
        parse_mode="Markdown"
    )

@dp.message(OrderForm.delivery)
async def get_delivery(message: types.Message, state: FSMContext):
    if "Самовывоз" in message.text:
        delivery = "🚗 Самовывоз (адрес сообщу после оплаты)"
    elif "Почта" in message.text:
        delivery = "📦 Отправка Почтой России (доставка за счет клиента)"
    elif "СДЭК" in message.text:
        delivery = "🚚 Отправка СДЭК (доставка за счет клиента)"
    else:
        await message.answer("❌ Пожалуйста, выберите способ получения из кнопок")
        return
    
    await state.update_data(delivery=delivery)
    await state.set_state(OrderForm.promo)
    await message.answer(
        "🎟 *Есть промокод?*\n\nВведите промокод или напишите 'пропустить':",
        reply_markup=cancel_kb,
        parse_mode="Markdown"
    )

@dp.message(OrderForm.promo)
async def get_promo(message: types.Message, state: FSMContext):
    promo = None if message.text.lower() == "пропустить" else message.text.upper()
    if promo:
        promocodes = load_json(PROMOCODES_FILE)
        if promo in promocodes and not promocodes[promo]["used"]:
            await state.update_data(promo=promo)
            await message.answer(f"✅ Промокод *{promo}* активирован! Вы получите скидку 10% после оплаты.", parse_mode="Markdown")
        else:
            await message.answer("❌ Неверный или уже использованный промокод. Продолжаем без скидки.")
            await state.update_data(promo=None)
    else:
        await state.update_data(promo=None)
    
    await state.set_state(OrderForm.model_type)
    await message.answer(
        "🔹 *У вас есть готовая модель?*\n\nВыберите вариант:",
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
            "⚠️ *Важно:* Перед отправкой проверьте модель на ошибки!\n"
            "Исполнитель не гарантирует качество печати при геометрических ошибках.\n\n"
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
            "• Особенности формы\n"
            "• Ссылки на референсы (если есть)\n\n"
            "Чем подробнее описание, тем точнее будет результат!\n\n"
            "💰 Стоимость дизайна обсуждается индивидуально.",
            reply_markup=cancel_kb,
            parse_mode="Markdown"
        )
    else:
        await message.answer("❌ Пожалуйста, выберите вариант из кнопок")

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
            "• Качество печати (черновая/стандартная/высокая)\n"
            "• Сроки\n"
            "• Особые требования\n\n"
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
    promo = user_data.get("promo")
    
    order = {
        "user_id": user_id,
        "username": message.from_user.username,
        "full_name": message.from_user.full_name,
        "name": user_data["name"],
        "contact": user_data["contact"],
        "delivery": user_data["delivery"],
        "promocode": promo,
        "model_type": user_data["model_type"],
        "files": user_data.get("files", []),
        "description": user_data["description"],
        "status": "new",
        "legal_accepted": True,
        "created_at": str(datetime.now())
    }
    
    orders = load_json(ORDERS_FILE)
    orders[str(user_id)] = order
    save_json(ORDERS_FILE, orders)
    
    await message.answer(
        "✅ *Заявка успешно отправлена!*\n\n"
        "Я передал её оператору.\n"
        "Статус заявки можно проверить командой /status\n\n"
        "📜 Напоминаем: работа начинается только после 100% предоплаты.",
        reply_markup=main_menu,
        parse_mode="Markdown"
    )
    
    if ADMIN_ID:
        await notify_admin(order, user_id)
    
    await state.clear()

async def notify_admin(order: dict, user_id: int):
    model_type_text = "✅ Готовая модель" if order["model_type"] == "ready" else "🎨 Требуется дизайн в Blender"
    
    text = (
        f"🔔 *НОВАЯ ЗАЯВКА!*\n"
        f"{'='*30}\n\n"
        f"👤 *Клиент:* {order['name']}\n"
        f"🆔 *Telegram ID:* {user_id}\n"
        f"📱 *Username:* @{order['username'] or 'Нет'}\n"
        f"📞 *Контакт:* {order['contact']}\n"
        f"🚚 *Доставка:* {order['delivery']}\n\n"
        f"🖨️ *Тип:* {model_type_text}\n\n"
        f"📝 *Пожелания:*\n{order['description']}\n"
    )
    
    if order.get("promocode"):
        text += f"\n🎟 *Промокод:* {order['promocode']}\n"
    
    if order["files"]:
        text += f"\n📁 *Файлов:* {len(order['files'])} шт.\n"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Написать клиенту", url=f"tg://user?id={user_id}")],
        [InlineKeyboardButton(text="✅ Принять", callback_data=f"accept_order_{user_id}"),
         InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_order_{user_id}")]
    ])
    
    await bot.send_message(ADMIN_ID, text, parse_mode="Markdown", reply_markup=kb)
    
    if order["files"]:
        for file in order["files"]:
            await bot.send_document(ADMIN_ID, file["file_id"], caption=file["name"])

# ========== ОБРАБОТКА ЗАЯВОК АДМИНА ==========
@dp.callback_query(lambda c: c.data.startswith(("accept_designer_", "reject_designer_", "accept_franchise_", "reject_franchise_", "accept_order_", "reject_order_")))
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
    
    elif role == "order":
        orders = load_json(ORDERS_FILE)
        if str(user_id) in orders:
            if action == "accept":
                orders[str(user_id)]["status"] = "accepted"
                save_json(ORDERS_FILE, orders)
                await bot.send_message(user_id, "✅ *Ваша заявка принята!* Скоро свяжемся.", parse_mode="Markdown")
            else:
                orders[str(user_id)]["status"] = "rejected"
                save_json(ORDERS_FILE, orders)
                await bot.send_message(user_id, "❌ Заявка отклонена.", parse_mode="Markdown")
            await callback.message.edit_text(callback.message.text + f"\n\n✅ {action.upper()}")
    
    await callback.answer()

@dp.message(Command("status"))
async def cmd_status(message: types.Message):
    orders = load_json(ORDERS_FILE)
    user_id = str(message.from_user.id)
    
    if user_id in orders:
        order = orders[user_id]
        status_text = {
            "new": "⏳ На рассмотрении",
            "accepted": "✅ Принята",
            "rejected": "❌ Отклонена"
        }.get(order.get("status", "new"), "❓ Неизвестно")
        
        await message.answer(
            f"📋 *Статус вашей заявки:* {status_text}\n\n"
            f"👤 Имя: {order['name']}\n"
            f"📞 Контакт: {order['contact']}\n"
            f"🚚 Доставка: {order.get('delivery', 'Не указана')}",
            parse_mode="Markdown"
        )
    else:
        await message.answer("❌ У вас нет активных заявок.", reply_markup=main_menu)

# ========== ЗАПУСК ==========
async def main():
    print("🚀 Бот ИП «Kildear» запущен!")
    print(f"✅ Токен: {TOKEN[:10]}...")
    print(f"✅ ADMIN_ID: {ADMIN_ID}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
