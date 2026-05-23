import os
import asyncio
import sys
import json
import random
import string
import qrcode
from io import BytesIO
from datetime import datetime, timedelta
from collections import defaultdict
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiohttp import web
from PIL import Image, ImageDraw, ImageFont

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

Нажимая "✅ Принимаю условия", вы подтверждаете согласие с данными правилами.
"""

# ========== ХРАНИЛИЩА ==========
ORDERS_FILE = "orders.json"
USERS_FILE = "users.json"
PARTNERS_FILE = "partners.json"
DESIGNERS_FILE = "designers.json"
FRANCHISE_FILE = "franchise.json"
PROMOCODES_FILE = "promocodes.json"
REVIEWS_FILE = "reviews.json"
DISCOUNT_REQUESTS_FILE = "discount_requests.json"

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

def generate_order_id():
    return f"ORD-{datetime.now().strftime('%Y%m%d')}-{random.randint(1000, 9999)}"

def generate_qr(data: str) -> BytesIO:
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes

# ========== СОСТОЯНИЯ ЗАКАЗА ==========
ORDER_STATUSES = {
    "new": "🆕 Новая заявка",
    "accepted": "✅ Принят",
    "in_progress": "🔧 В работе",
    "almost_ready": "⚡ Почти готов",
    "ready": "🎉 Готов к выдаче",
    "completed": "🏁 Завершен",
    "rejected": "❌ Отклонен"
}

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

class ReviewForm(StatesGroup):
    rating = State()
    text = State()
    photo = State()

class DiscountRequest(StatesGroup):
    reason = State()

# ========== КЛАВИАТУРЫ ==========
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📝 Оставить заявку")],
        [KeyboardButton(text="📊 Мои заказы"), KeyboardButton(text="⭐ Оставить отзыв")],
        [KeyboardButton(text="💰 Запросить скидку"), KeyboardButton(text="🎟 Промокоды")],
        [KeyboardButton(text="🤝 Стать партнером"), KeyboardButton(text="🎨 Стать дизайнером")],
        [KeyboardButton(text="🏭 Стать частью фирмы"), KeyboardButton(text="📜 Правилы")]
    ],
    resize_keyboard=True
)

admin_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="📈 Отчеты")],
        [KeyboardButton(text="💰 Запросы скидок"), KeyboardButton(text="⭐ Отзывы")],
        [KeyboardButton(text="🎟 Управление промокодами"), KeyboardButton(text="📦 Все заказы")],
        [KeyboardButton(text="👥 Пользователи"), KeyboardButton(text="🔄 Изменить статус")]
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
    # Сохраняем пользователя
    users = load_json(USERS_FILE)
    user_id = str(message.from_user.id)
    if user_id not in users:
        users[user_id] = {
            "user_id": message.from_user.id,
            "username": message.from_user.username,
            "full_name": message.from_user.full_name,
            "first_seen": str(datetime.now()),
            "total_orders": 0,
            "total_spent": 0
        }
        save_json(USERS_FILE, users)
    
    await message.answer(
        "🏭 *ИП «Kildear» - 3D печать*\n\n"
        "Выберите действие:",
        reply_markup=main_menu if message.from_user.id != ADMIN_ID else admin_menu,
        parse_mode="Markdown"
    )

@dp.message(Command("rules"))
async def cmd_rules(message: types.Message):
    await message.answer(LEGAL_TEXT, parse_mode="Markdown")

@dp.message(F.text == "📜 Правилы")
async def rules_button(message: types.Message):
    await message.answer(LEGAL_TEXT, parse_mode="Markdown")

@dp.message(Command("status"))
async def cmd_status(message: types.Message):
    orders = load_json(ORDERS_FILE)
    user_id = str(message.from_user.id)
    
    user_orders = [o for o in orders.values() if o["user_id"] == message.from_user.id]
    if not user_orders:
        await message.answer("❌ У вас нет активных заявок.", reply_markup=main_menu)
        return
    
    latest = user_orders[-1]
    status_text = ORDER_STATUSES.get(latest["status"], "❓ Неизвестно")
    
    await message.answer(
        f"📋 *Статус вашей заявки:* {status_text}\n\n"
        f"👤 Имя: {latest['name']}\n"
        f"📞 Контакт: {latest['contact']}\n"
        f"🚚 Доставка: {latest.get('delivery', 'Не указана')}\n"
        f"🆔 Номер заказа: {latest.get('order_id', 'Нет')}",
        parse_mode="Markdown"
    )

# ========== НОВЫЕ КОМАНДЫ ==========
@dp.message(F.text == "📊 Мои заказы")
async def my_orders(message: types.Message):
    orders = load_json(ORDERS_FILE)
    user_orders = [o for o in orders.values() if o["user_id"] == message.from_user.id]
    
    if not user_orders:
        await message.answer("❌ У вас пока нет заказов.", reply_markup=main_menu)
        return
    
    text = "📋 *Ваши заказы:*\n\n"
    for order in user_orders[-5:]:
        status = ORDER_STATUSES.get(order["status"], "❓ Неизвестно")
        text += f"🔹 *{order.get('order_id', 'Без номера')}*\n"
        text += f"   Статус: {status}\n"
        text += f"   Дата: {order['created_at'][:10]}\n"
        text += f"   Сумма: {order.get('price', 'Не указана')}₽\n\n"
    
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text == "⭐ Оставить отзыв")
async def start_review(message: types.Message, state: FSMContext):
    orders = load_json(ORDERS_FILE)
    user_orders = [o for o in orders.values() if o["user_id"] == message.from_user.id and o["status"] == "completed"]
    
    if not user_orders:
        await message.answer("❌ У вас нет завершенных заказов для отзыва.\n\nЗакажите что-нибудь и после завершения сможете оставить отзыв!", reply_markup=main_menu)
        return
    
    await state.set_state(ReviewForm.rating)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐"*i, callback_data=f"rating_{i}") for i in range(1, 6)]
    ])
    await message.answer("⭐ *Оцените нашу работу от 1 до 5:*", parse_mode="Markdown", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data.startswith("rating_"))
async def get_rating(callback: types.CallbackQuery, state: FSMContext):
    rating = int(callback.data.split("_")[1])
    await state.update_data(rating=rating)
    await state.set_state(ReviewForm.text)
    await callback.message.edit_text(f"⭐ Вы выбрали {rating} звезд(ы)\n\n📝 Напишите ваш отзыв подробнее:")
    await callback.answer()

@dp.message(ReviewForm.text)
async def get_review_text(message: types.Message, state: FSMContext):
    await state.update_data(text=message.text)
    await state.set_state(ReviewForm.photo)
    await message.answer("📸 Прикрепите фото (опционально) или напишите 'пропустить':", reply_markup=cancel_kb)

@dp.message(ReviewForm.photo)
async def get_review_photo(message: types.Message, state: FSMContext):
    data = await state.get_data()
    photo_id = None
    
    if message.photo:
        photo_id = message.photo[-1].file_id
    elif message.text and message.text.lower() == "пропустить":
        pass
    else:
        await message.answer("Отправьте фото или напишите 'пропустить'")
        return
    
    review = {
        "user_id": message.from_user.id,
        "username": message.from_user.username,
        "rating": data["rating"],
        "text": data["text"],
        "photo": photo_id,
        "created_at": str(datetime.now())
    }
    
    reviews = load_json(REVIEWS_FILE)
    reviews[str(datetime.now().timestamp())] = review
    save_json(REVIEWS_FILE, reviews)
    
    await message.answer("✅ *Спасибо за отзыв!* Он очень важен для нас.", parse_mode="Markdown", reply_markup=main_menu)
    
    if ADMIN_ID:
        await bot.send_message(ADMIN_ID, f"⭐ *Новый отзыв!*\nОценка: {data['rating']}/5\nТекст: {data['text']}")
    
    await state.clear()

@dp.message(F.text == "💰 Запросить скидку")
async def request_discount(message: types.Message, state: FSMContext):
    await state.set_state(DiscountRequest.reason)
    await message.answer(
        "💸 *Запрос скидки*\n\n"
        "Опишите причину запроса скидки:\n"
        "• Объем заказа\n"
        "• Постоянное сотрудничество\n"
        "• Акция или промокод\n\n"
        "Администратор рассмотрит ваш запрос:",
        parse_mode="Markdown",
        reply_markup=cancel_kb
    )

@dp.message(DiscountRequest.reason)
async def process_discount_request(message: types.Message, state: FSMContext):
    request = {
        "user_id": message.from_user.id,
        "username": message.from_user.username,
        "reason": message.text,
        "status": "pending",
        "created_at": str(datetime.now())
    }
    
    discount_requests = load_json(DISCOUNT_REQUESTS_FILE)
    discount_requests[str(datetime.now().timestamp())] = request
    save_json(DISCOUNT_REQUESTS_FILE, discount_requests)
    
    await message.answer(
        "✅ *Запрос отправлен!*\n\n"
        "Администратор рассмотрит его и свяжется с вами.",
        parse_mode="Markdown",
        reply_markup=main_menu
    )
    
    if ADMIN_ID:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💰 Одобрить скидку", callback_data=f"approve_discount_{request['user_id']}")]
        ])
        await bot.send_message(
            ADMIN_ID,
            f"💰 *Новый запрос скидки!*\n"
            f"👤 @{request['username']}\n"
            f"📝 Причина: {request['reason']}",
            reply_markup=keyboard
        )
    
    await state.clear()

@dp.message(F.text == "🎟 Промокоды")
async def my_promocodes(message: types.Message):
    partners = load_json(PARTNERS_FILE)
    user_id = str(message.from_user.id)
    
    if user_id in partners:
        promo = partners[user_id].get("promocode")
        await message.answer(
            f"🎟 *Ваш промокод:* `{promo}`\n\n"
            f"Дайте его друзьям, они получат скидку 10%, а вы 10% от их заказа!\n\n"
            f"💰 Ваш баланс: {partners[user_id].get('balance', 0)}₽",
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            "🎟 *У вас нет промокода*\n\n"
            "Станьте партнером через кнопку 🤝 Стать партнером и получите свой промокод!",
            parse_mode="Markdown"
        )

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

# ========== ОСНОВНАЯ ЗАЯВКА (СОХРАНЯЕМ ПОЛНОСТЬЮ) ==========
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
        reply_markup=main_menu if message.from_user.id != ADMIN_ID else admin_menu
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
    order_id = generate_order_id()
    
    order = {
        "order_id": order_id,
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
        "created_at": str(datetime.now()),
        "price": None,
        "final_price": None
    }
    
    orders = load_json(ORDERS_FILE)
    orders[order_id] = order
    save_json(ORDERS_FILE, orders)
    
    await message.answer(
        "✅ *Заявка успешно отправлена!*\n\n"
        f"🆔 Номер заказа: `{order_id}`\n\n"
        "Я передал её оператору.\n"
        "Статус заявки можно проверить командой /status\n\n"
        "📜 Напоминаем: работа начинается только после 100% предоплаты.",
        reply_markup=main_menu if message.from_user.id != ADMIN_ID else admin_menu,
        parse_mode="Markdown"
    )
    
    if ADMIN_ID:
        await notify_admin(order, user_id)
    
    await state.clear()

async def generate_receipt(order: dict) -> BytesIO:
    """Генерация чека в виде изображения"""
    img = Image.new('RGB', (800, 1000), color='white')
    draw = ImageDraw.Draw(img)
    
    try:
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
        font_normal = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
    except:
        font_title = ImageFont.load_default()
        font_normal = ImageFont.load_default()
    
    y = 50
    draw.text((50, y), "🧾 ЧЕК ОБ ОПЛАТЕ", fill='black', font=font_title)
    y += 60
    
    receipt_data = [
        ("Номер заказа", order.get("order_id", "Нет")),
        ("Дата", datetime.now().strftime("%d.%m.%Y %H:%M")),
        ("Клиент", f"{order.get('name', 'Нет')} (@{order.get('username', 'Нет username')})"),
        ("Тип", "Готовая модель" if order.get("model_type") == "ready" else "Дизайн + печать"),
        ("Сумма", f"{order.get('price', 0)} ₽"),
        ("Статус", "Оплачено"),
        ("Способ получения", order.get("delivery", "Не указан")),
        ("Промокод", order.get("promocode", "Не использован")),
    ]
    
    for label, value in receipt_data:
        draw.text((50, y), f"{label}:", fill='black', font=font_normal)
        draw.text((250, y), str(value), fill='black', font=font_normal)
        y += 40
    
    draw.text((50, y), "Спасибо за заказ!", fill='black', font=font_title)
    
    qr_data = f"Заказ: {order.get('order_id')}\nСумма: {order.get('price', 0)}₽\nДата: {datetime.now()}"
    qr_img = generate_qr(qr_data)
    qr_pil = Image.open(qr_img)
    qr_pil = qr_pil.resize((200, 200))
    img.paste(qr_pil, (300, y + 20))
    
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    return img_bytes

async def notify_admin(order: dict, user_id: int):
    model_type_text = "✅ Готовая модель" if order["model_type"] == "ready" else "🎨 Требуется дизайн в Blender"
    
    text = (
        f"🔔 *НОВАЯ ЗАЯВКА!*\n"
        f"{'='*30}\n\n"
        f"🆔 *Номер:* {order['order_id']}\n"
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
    
    if order.get("files"):
        text += f"\n📁 *Файлов:* {len(order['files'])} шт.\n"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Написать клиенту", url=f"tg://user?id={user_id}")],
        [InlineKeyboardButton(text="✅ Принять", callback_data=f"accept_order_{order['order_id']}"),
         InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_order_{order['order_id']}")]
    ])
    
    await bot.send_message(ADMIN_ID, text, parse_mode="Markdown", reply_markup=kb)
    
    if order.get("files"):
        for file in order["files"]:
            await bot.send_document(ADMIN_ID, file["file_id"], caption=file["name"])

# ========== АДМИН-ФУНКЦИИ (НОВЫЕ) ==========
@dp.message(F.text == "📊 Статистика")
async def admin_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Только для админа")
        return
    
    orders = load_json(ORDERS_FILE)
    users = load_json(USERS_FILE)
    reviews = load_json(REVIEWS_FILE)
    
    total_orders = len(orders)
    completed_orders = len([o for o in orders.values() if o.get("status") == "completed"])
    total_users = len(users)
    avg_rating = sum([r["rating"] for r in reviews.values()]) / len(reviews) if reviews else 0
    total_revenue = sum([o.get("price", 0) for o in orders.values() if o.get("price")])
    
    text = (
        f"📊 *СТАТИСТИКА БОТА*\n\n"
        f"👥 Пользователей: {total_users}\n"
        f"📦 Всего заказов: {total_orders}\n"
        f"✅ Завершено: {completed_orders}\n"
        f"⭐ Средний рейтинг: {avg_rating:.1f}/5\n"
        f"💰 Выручка: {total_revenue}₽"
    )
    
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text == "📈 Отчеты")
async def admin_reports(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 За неделю", callback_data="report_week"),
         InlineKeyboardButton(text="📆 За месяц", callback_data="report_month")],
        [InlineKeyboardButton(text="📊 За год", callback_data="report_year"),
         InlineKeyboardButton(text="📈 За все время", callback_data="report_all")]
    ])
    
    await message.answer("📊 *Выберите период для отчета:*", parse_mode="Markdown", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data.startswith("report_"))
async def generate_report(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Только для админа")
        return
    
    period = callback.data.split("_")[1]
    orders = load_json(ORDERS_FILE)
    
    now = datetime.now()
    if period == "week":
        start_date = now - timedelta(days=7)
        period_name = "неделю"
    elif period == "month":
        start_date = now - timedelta(days=30)
        period_name = "месяц"
    elif period == "year":
        start_date = now - timedelta(days=365)
        period_name = "год"
    else:
        start_date = datetime(2020, 1, 1)
        period_name = "все время"
    
    filtered_orders = []
    for order in orders.values():
        order_date = datetime.fromisoformat(order["created_at"])
        if order_date >= start_date:
            filtered_orders.append(order)
    
    total_orders = len(filtered_orders)
    total_revenue = sum([o.get("price", 0) for o in filtered_orders if o.get("price")])
    avg_price = total_revenue / total_orders if total_orders else 0
    
    status_counts = defaultdict(int)
    for order in filtered_orders:
        status_counts[order.get("status", "new")] += 1
    
    text = f"📊 *Отчет за {period_name}*\n\n"
    text += f"📦 Заказов: {total_orders}\n"
    text += f"💰 Выручка: {total_revenue}₽\n"
    text += f"💵 Средний чек: {avg_price:.0f}₽\n\n"
    text += "*По статусам:*\n"
    for status, count in status_counts.items():
        text += f"• {ORDER_STATUSES.get(status, status)}: {count}\n"
    
    import csv
    csv_file = f"report_{period}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with open(csv_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Номер заказа", "Клиент", "Статус", "Сумма", "Дата"])
        for order in filtered_orders:
            writer.writerow([
                order.get("order_id", "Нет"),
                order.get("name", "Нет"),
                ORDER_STATUSES.get(order.get("status", "new"), order.get("status", "new")),
                order.get("price", 0),
                order["created_at"][:10]
            ])
    
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.message.answer_document(FSInputFile(csv_file))
    os.remove(csv_file)
    await callback.answer()

@dp.message(F.text == "💰 Запросы скидок")
async def view_discount_requests(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    requests = load_json(DISCOUNT_REQUESTS_FILE)
    pending = {k: v for k, v in requests.items() if v.get("status") == "pending"}
    
    if not pending:
        await message.answer("❌ Нет активных запросов на скидку")
        return
    
    text = "💰 *Запросы на скидку:*\n\n"
    for req_id, req in list(pending.items())[:10]:
        text += f"👤 @{req.get('username', 'Нет')}\n"
        text += f"📝 {req.get('reason', 'Нет')[:100]}\n"
        text += f"📅 {req.get('created_at', '')[:10]}\n\n"
    
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text == "⭐ Отзывы")
async def view_reviews(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    reviews = load_json(REVIEWS_FILE)
    if not reviews:
        await message.answer("❌ Отзывов пока нет")
        return
    
    text = "⭐ *Последние отзывы:*\n\n"
    for review in list(reviews.values())[-10:]:
        text += f"👤 @{review.get('username', 'Нет')}\n"
        text += f"⭐ {review.get('rating', 0)}/5\n"
        text += f"📝 {review.get('text', '')[:100]}\n"
        text += f"📅 {review.get('created_at', '')[:10]}\n\n"
    
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text == "🎟 Управление промокодами")
async def manage_promocodes(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Создать промокод", callback_data="create_promo")],
        [InlineKeyboardButton(text="📋 Список промокодов", callback_data="list_promos")]
    ])
    
    await message.answer("🎟 *Управление промокодами*", parse_mode="Markdown", reply_markup=keyboard)

@dp.message(F.text == "📦 Все заказы")
async def all_orders_admin(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    orders = load_json(ORDERS_FILE)
    if not orders:
        await message.answer("❌ Заказов пока нет")
        return
    
    text = "📦 *Все заказы:*\n\n"
    for order in list(orders.values())[-20:]:
        text += f"🔹 *{order.get('order_id', 'Нет')}*\n"
        text += f"   👤 {order.get('name', 'Нет')}\n"
        text += f"   📊 {ORDER_STATUSES.get(order.get('status', 'new'), order.get('status', 'new'))}\n"
        text += f"   💰 {order.get('price', 'Не указана')}₽\n"
        text += f"   📅 {order.get('created_at', '')[:10]}\n\n"
    
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text == "👥 Пользователи")
async def list_users(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    users = load_json(USERS_FILE)
    text = "👥 *Пользователи:*\n\n"
    for user in list(users.values())[-20:]:
        text += f"👤 @{user.get('username', 'Нет username')}\n"
        text += f"   📦 Заказов: {user.get('total_orders', 0)}\n"
        text += f"   💰 Потрачено: {user.get('total_spent', 0)}₽\n"
        text += f"   📅 {user.get('first_seen', '')[:10]}\n\n"
    
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text == "🔄 Изменить статус")
async def change_status_menu(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    orders = load_json(ORDERS_FILE)
    keyboard = []
    for order_id, order in list(orders.items())[-10:]:
        keyboard.append([InlineKeyboardButton(
            text=f"#{order.get('order_id', order_id)} - {order.get('name', 'Нет')}",
            callback_data=f"select_order_{order_id}"
        )])
    
    await message.answer("📦 *Выберите заказ для изменения статуса:*", 
                        parse_mode="Markdown",
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@dp.callback_query(lambda c: c.data.startswith("select_order_"))
async def select_order_for_status(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Только для админа")
        return
    
    order_id = callback.data.split("_")[2]
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Принят", callback_data=f"set_status_{order_id}_accepted")],
        [InlineKeyboardButton(text="🔧 В работе", callback_data=f"set_status_{order_id}_in_progress")],
        [InlineKeyboardButton(text="⚡ Почти готов", callback_data=f"set_status_{order_id}_almost_ready")],
        [InlineKeyboardButton(text="🎉 Готов", callback_data=f"set_status_{order_id}_ready")],
        [InlineKeyboardButton(text="🏁 Завершен", callback_data=f"set_status_{order_id}_completed")],
        [InlineKeyboardButton(text="❌ Отклонен", callback_data=f"set_status_{order_id}_rejected")]
    ])
    
    await callback.message.edit_text(f"🎯 *Выберите новый статус для заказа {order_id}:*", 
                                     parse_mode="Markdown",
                                     reply_markup=keyboard)

@dp.callback_query(lambda c: c.data.startswith(("set_status_", "accept_order_", "reject_order_", "accept_designer_", "reject_designer_", "accept_franchise_", "reject_franchise_", "approve_discount_")))
async def handle_admin_actions(callback: types.CallbackQuery):
    if ADMIN_ID and callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Только для админа", show_alert=True)
        return
    
    action = callback.data.split("_")[0]
    
    # Принятие/отклонение заказа
    if action in ["accept", "reject"] and "order" in callback.data:
        _, action, order_id = callback.data.split("_")
        orders = load_json(ORDERS_FILE)
        
        if order_id in orders:
            if action == "accept":
                orders[order_id]["status"] = "accepted"
                save_json(ORDERS_FILE, orders)
                await bot.send_message(
                    orders[order_id]["user_id"],
                    f"✅ *Ваша заявка {order_id} принята!*\n\nСкоро свяжемся для согласования цены.",
                    parse_mode="Markdown"
                )
                # Запрашиваем цену у админа
                await callback.message.answer(f"💰 Введите цену для заказа {order_id} в рублях:")
                # Сохраняем для установки цены
                await callback.message.answer("(просто отправьте число)")
            else:
                orders[order_id]["status"] = "rejected"
                save_json(ORDERS_FILE, orders)
                await bot.send_message(
                    orders[order_id]["user_id"],
                    f"❌ *Заявка {order_id} отклонена.*\n\nПо вопросам пишите администратору.",
                    parse_mode="Markdown"
                )
            await callback.message.edit_text(f"✅ Заказ {order_id} {action}ен")
    
    # Изменение статуса заказа
    elif action == "set":
        _, _, order_id, status = callback.data.split("_")
        orders = load_json(ORDERS_FILE)
        
        if order_id in orders:
            old_status = orders[order_id].get("status", "new")
            orders[order_id]["status"] = status
            save_json(ORDERS_FILE, orders)
            
            status_text = ORDER_STATUSES.get(status, status)
            await bot.send_message(
                orders[order_id]["user_id"],
                f"🔄 *Статус заказа {order_id} обновлен!*\n\n📊 Новый статус: {status_text}",
                parse_mode="Markdown"
            )
            
            # Если заказ завершен, обновляем статистику пользователя
            if status == "completed":
                users = load_json(USERS_FILE)
                user_id = str(orders[order_id]["user_id"])
                if user_id in users:
                    users[user_id]["total_orders"] = users[user_id].get("total_orders", 0) + 1
                    users[user_id]["total_spent"] = users[user_id].get("total_spent", 0) + orders[order_id].get("price", 0)
                    save_json(USERS_FILE, users)
                
                await bot.send_message(
                    orders[order_id]["user_id"],
                    "🎉 *Ваш заказ завершен!*\n\nПожалуйста, оставьте отзыв через кнопку ⭐ Оставить отзыв.",
                    parse_mode="Markdown"
                )
                
                # Генерируем и отправляем чек при завершении
                receipt_img = await generate_receipt(orders[order_id])
                await bot.send_photo(
                    orders[order_id]["user_id"],
                    types.BufferedInputFile(receipt_img.getvalue(), filename="receipt.png"),
                    caption=f"🧾 *Чек об оплате заказа {order_id}*\n\nСохраните для отчетности."
                )
            
            await callback.message.edit_text(f"✅ Статус заказа {order_id} изменен на {status_text}")
    
    # Одобрение скидки
    elif action == "approve":
        _, _, user_id = callback.data.split("_")
        await callback.message.answer(f"💰 Введите размер скидки в % для пользователя @{user_id}:")
        # Здесь можно добавить сохранение скидки
    
    # Дизайнеры и франшизы
    elif action in ["accept", "reject"]:
        parts = callback.data.split("_")
        action = parts[0]
        role = parts[1]
        user_id = int(parts[2])
        
        if role == "designer":
            designers = load_json(DESIGNERS_FILE)
            if str(user_id) in designers:
                if action == "accept":
                    designers[str(user_id)]["status"] = "accepted"
                    await bot.send_message(user_id, "✅ *Заявка дизайнера одобрена!* С вами свяжутся.", parse_mode="Markdown")
                else:
                    designers[str(user_id)]["status"] = "rejected"
                    await bot.send_message(user_id, "❌ Заявка отклонена.", parse_mode="Markdown")
                save_json(DESIGNERS_FILE, designers)
        
        elif role == "franchise":
            franchises = load_json(FRANCHISE_FILE)
            if str(user_id) in franchises:
                if action == "accept":
                    franchises[str(user_id)]["status"] = "accepted"
                    await bot.send_message(user_id, "✅ *Вы стали частью фирмы!* 80% вам, 20% нам.", parse_mode="Markdown")
                else:
                    franchises[str(user_id)]["status"] = "rejected"
                    await bot.send_message(user_id, "❌ Заявка отклонена.", parse_mode="Markdown")
                save_json(FRANCHISE_FILE, franchises)
        
        await callback.message.edit_text(callback.message.text + f"\n\n✅ {action.upper()}")
    
    await callback.answer()

# ========== ВЕБ-СЕРВЕР ДЛЯ RENDER ==========
async def health_check(request):
    return web.Response(text="OK")

async def start_web_server():
    app_web = web.Application()
    app_web.router.add_get("/", health_check)
    runner = web.AppRunner(app_web)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"✅ Веб-сервер запущен на порту {port}")

# ========== ЗАПУСК ==========
async def main():
    await start_web_server()
    print("🚀 Бот ИП «Kildear» запущен!")
    print(f"✅ Токен: {TOKEN[:10]}...")
    print(f"✅ ADMIN_ID: {ADMIN_ID}")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
