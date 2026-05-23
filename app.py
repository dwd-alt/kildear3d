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

def generate_receipt_number():
    """Генерация внутреннего номера квитанции"""
    return f"INV-{datetime.now().strftime('%Y%m%d')}-{random.randint(100000, 999999)}"

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

class InvoiceForm(StatesGroup):
    """Форма для заполнения квитанции"""
    price = State()
    material = State()
    color = State()
    quantity = State()
    discount = State()
    delivery_price = State()
    delivery_address = State()
    payment_method = State()
    comment = State()
    tracking_number = State()
    ready_days = State()
    future_promo = State()
    confirm = State()

# ========== КЛАВИАТУРЫ ==========
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📝 Оставить заявку")],
        [KeyboardButton(text="📊 Мои заказы"), KeyboardButton(text="⭐ Оставить отзыв")],
        [KeyboardButton(text="💰 Запросить скидку"), KeyboardButton(text="🎟 Промокоды")],
        [KeyboardButton(text="🤝 Стать партнером"), KeyboardButton(text="🎨 Стать дизайнером")],
        [KeyboardButton(text="🏭 Стать частью фирмы"), KeyboardButton(text="📜 Правила")]
    ],
    resize_keyboard=True
)

admin_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="📈 Отчеты")],
        [KeyboardButton(text="💰 Запросы скидок"), KeyboardButton(text="⭐ Отзывы")],
        [KeyboardButton(text="🎟 Управление промокодами"), KeyboardButton(text="📦 Все заказы")],
        [KeyboardButton(text="👥 Пользователи"), KeyboardButton(text="🔄 Изменить статус")],
        [KeyboardButton(text="📋 Создать квитанцию")]
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

# ========== ГЕНЕРАЦИЯ КВИТАНЦИИ (НЕ ЧЕК!) ==========
async def generate_invoice(order: dict, payment_data: dict = None) -> BytesIO:
    """
    Генерация информационной квитанции об оплате
    ВНИМАНИЕ: Это НЕ фискальный чек, а просто внутренний документ
    Фискальный чек отправляется отдельно через ККТ при необходимости
    """
    img = Image.new('RGB', (900, 1550), color='white')
    draw = ImageDraw.Draw(img)
    
    try:
        font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
        font_header = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
        font_normal = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        font_bold_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
    except:
        font_title = ImageFont.load_default()
        font_header = ImageFont.load_default()
        font_normal = ImageFont.load_default()
        font_small = ImageFont.load_default()
        font_bold_small = ImageFont.load_default()
    
    y = 40
    x = 50
    
    # Заголовок
    draw.text((x, y), "📋 КВИТАНЦИЯ ОБ ОПЛАТЕ", fill='black', font=font_title)
    y += 45
    draw.text((x, y), "Внутренний документ (не является фискальным чеком)", fill='gray', font=font_small)
    y += 35
    
    # Рамка
    draw.rectangle([x-10, y-10, 850, y + 680], outline='black', width=2)
    
    # Данные магазина
    draw.text((x, y), "🏭 ИП «Kildear»", fill='black', font=font_header)
    y += 40
    draw.text((x, y), f"ИНН: {payment_data.get('inn', '1234567890')}", fill='gray', font=font_small)
    y += 25
    draw.text((x, y), f"ОГРНИП: {payment_data.get('ogrnip', '123456789012345')}", fill='gray', font=font_small)
    y += 40
    
    # Номер квитанции
    invoice_number = generate_receipt_number()
    draw.text((x, y), f"КВИТАНЦИЯ №: {invoice_number}", fill='black', font=font_normal)
    y += 35
    
    # Линия разделитель
    draw.line([x, y, 850, y], fill='black', width=1)
    y += 20
    
    # Детали заказа
    draw.text((x, y), "📋 ДЕТАЛИ ЗАКАЗА", fill='black', font=font_header)
    y += 40
    
    invoice_data = [
        ("Номер заказа", order.get("order_id", "Нет")),
        ("Дата выставления", payment_data.get('date', datetime.now().strftime("%d.%m.%Y %H:%M"))),
        ("Способ оплаты", payment_data.get('payment_method', 'Перевод по реквизитам')),
        ("Статус оплаты", "Ожидает подтверждения"),
    ]
    
    for label, value in invoice_data:
        draw.text((x, y), f"{label}:", fill='black', font=font_normal)
        draw.text((x + 220, y), str(value), fill='black', font=font_normal)
        y += 35
    
    y += 10
    draw.line([x, y, 850, y], fill='black', width=1)
    y += 20
    
    # Данные клиента
    draw.text((x, y), "👤 ДАННЫЕ КЛИЕНТА", fill='black', font=font_header)
    y += 40
    
    username = order.get("username", "Нет username")
    if username and username != "Нет username":
        username_display = f"@{username}"
    else:
        username_display = order.get("contact", "Не указан")
    
    client_data = [
        ("Имя", order.get("name", "Не указано")),
        ("Telegram", username_display),
        ("Контакты", order.get("contact", "Не указаны")),
        ("Адрес доставки", payment_data.get('delivery_address', order.get("delivery", "Самовывоз"))),
    ]
    
    for label, value in client_data:
        draw.text((x, y), f"{label}:", fill='black', font=font_normal)
        draw.text((x + 220, y), str(value), fill='black', font=font_normal)
        y += 35
    
    y += 10
    draw.line([x, y, 850, y], fill='black', width=1)
    y += 20
    
    # Информация о заказе
    draw.text((x, y), "🖨️ ИНФОРМАЦИЯ О ЗАКАЗЕ", fill='black', font=font_header)
    y += 40
    
    order_data = [
        ("Тип работы", "Готовая модель" if order.get("model_type") == "ready" else "Дизайн + печать"),
        ("Материал", payment_data.get('material', 'Не указан')),
        ("Цвет", payment_data.get('color', 'Не указан')),
        ("Количество", str(payment_data.get('quantity', 1)) + " шт."),
        ("Промокод", order.get("promocode", "Не использован")),
        ("Ориентировочный срок", payment_data.get('ready_days', '3-5 рабочих дней')),
    ]
    
    for label, value in order_data:
        draw.text((x, y), f"{label}:", fill='black', font=font_normal)
        draw.text((x + 220, y), str(value), fill='black', font=font_normal)
        y += 35
    
    # Трек-номер
    if payment_data.get('tracking_number'):
        y += 10
        draw.text((x, y), "📦 Трек-номер:", fill='black', font=font_normal)
        draw.text((x + 220, y), payment_data['tracking_number'], fill='blue', font=font_bold_small)
        y += 35
        draw.text((x, y), "Сайт отслеживания:", fill='black', font=font_small)
        draw.text((x + 220, y), "https://www.pochta.ru/tracking", fill='blue', font=font_small)
        y += 35
    
    y += 10
    draw.line([x, y, 850, y], fill='black', width=1)
    y += 20
    
    # Финансовая информация
    draw.text((x, y), "💰 ФИНАНСЫ", fill='black', font=font_header)
    y += 40
    
    original_price = payment_data.get('price', 0)
    discount = payment_data.get('discount', 0)
    final_price = original_price * (100 - discount) / 100
    delivery_price = payment_data.get('delivery_price', 0)
    total = final_price + delivery_price
    
    finance_data = [
        ("Стоимость печати", f"{original_price} ₽"),
        ("Скидка", f"{discount}%" if discount > 0 else "0%"),
        ("Сумма со скидкой", f"{final_price:.2f} ₽"),
        ("Доставка", f"{delivery_price} ₽"),
        ("ИТОГО К ОПЛАТЕ", f"{total:.2f} ₽"),
    ]
    
    for label, value in finance_data:
        draw.text((x, y), f"{label}:", fill='black', font=font_normal)
        if label == "ИТОГО К ОПЛАТЕ":
            draw.text((x + 220, y), value, fill='red', font=font_header)
        else:
            draw.text((x + 220, y), value, fill='black', font=font_normal)
        y += 40
    
    # Промокод на будущее
    if payment_data.get('future_promo'):
        y += 10
        draw.text((x, y), "🎟 ПРОМОКОД НА БУДУЩЕЕ", fill='black', font=font_header)
        y += 40
        draw.text((x, y), f"Ваш промокод:", fill='black', font=font_normal)
        draw.text((x + 220, y), payment_data['future_promo'], fill='green', font=font_bold_small)
        y += 35
        draw.text((x, y), "Скидка:", fill='black', font=font_normal)
        draw.text((x + 220, y), "10% на следующий заказ", fill='gray', font=font_small)
    
    # Комментарий
    if payment_data.get('comment'):
        y += 30
        draw.text((x, y), "📝 Комментарий:", fill='black', font=font_normal)
        y += 25
        comment_text = payment_data['comment']
        max_len = 60
        for i in range(0, len(comment_text), max_len):
            draw.text((x, y), comment_text[i:i+max_len], fill='gray', font=font_small)
            y += 25
    
    # QR код с данными заказа
    y = 1100
    draw.text((x, y), "📱 QR КОД С ДАННЫМИ ЗАКАЗА", fill='black', font=font_header)
    y += 50
    
    qr_data = f"""ЗАКАЗ #{order.get("order_id")}
Клиент: @{username if username != "Нет username" else order.get("name")}
Сумма: {total:.2f} ₽
Дата: {payment_data.get('date', datetime.now().strftime("%d.%m.%Y"))}
Трек-номер: {payment_data.get('tracking_number', 'Нет')}
Промокод: {payment_data.get('future_promo', 'Нет')}"""
    
    qr_img = generate_qr(qr_data)
    qr_pil = Image.open(qr_img)
    qr_pil = qr_pil.resize((200, 200))
    img.paste(qr_pil, (350, y))
    
    # Подпись
    y = 1400
    draw.line([x, y, 850, y], fill='black', width=1)
    y += 20
    draw.text((x, y), "Спасибо за заказ!", fill='black', font=font_small)
    draw.text((x + 400, y), "Подпись: __________", fill='black', font=font_small)
    y += 25
    draw.text((x + 350, y), datetime.now().strftime("%d.%m.%Y %H:%M"), fill='gray', font=font_small)
    
    # Важное примечание
    y += 40
    draw.text((x, y), "⚠️ Данная квитанция не является фискальным чеком и носит информационный характер", 
              fill='red', font=font_small)
    
    img_bytes = BytesIO()
    img.save(img_bytes, format='PNG', dpi=(300, 300))
    img_bytes.seek(0)
    return img_bytes

# ========== ОСНОВНЫЕ КОМАНДЫ ==========
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
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

@dp.message(F.text == "📜 Правила")
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
        await message.answer("❌ У вас нет завершенных заказов для отзыва.", reply_markup=main_menu)
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

# ========== АДМИН-ФУНКЦИИ ==========
@dp.message(F.text == "📋 Создать квитанцию")
async def start_invoice_creation(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        await message.answer("❌ Только для админа")
        return
    
    orders = load_json(ORDERS_FILE)
    keyboard = []
    for order_id, order in list(orders.items())[-10:]:
        keyboard.append([InlineKeyboardButton(
            text=f"#{order.get('order_id', order_id)} - {order.get('name', 'Нет')}",
            callback_data=f"create_invoice_{order_id}"
        )])
    
    await message.answer(
        "📋 *Выберите заказ для создания квитанции:*\n\n"
        "⚠️ ВНИМАНИЕ: Это информационная квитанция, не являющаяся фискальным чеком",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

@dp.callback_query(lambda c: c.data.startswith("create_invoice_"))
async def start_invoice_fill(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Только для админа")
        return
    
    order_id = callback.data.split("_")[2]
    await state.update_data(order_id=order_id)
    
    await state.set_state(InvoiceForm.price)
    await callback.message.answer(
        "💰 *Создание квитанции*\n\n"
        "Введите стоимость (в рублях):\n"
        "Пример: `1500`",
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.message(InvoiceForm.price)
async def invoice_price(message: types.Message, state: FSMContext):
    try:
        price = int(message.text)
        await state.update_data(price=price)
        await state.set_state(InvoiceForm.material)
        await message.answer(
            "🖨️ *Материал:*\n\n"
            "Напишите материал:\n"
            "PLA / PETG / ABS / Смола / Другое",
            parse_mode="Markdown"
        )
    except:
        await message.answer("❌ Введите число")

@dp.message(InvoiceForm.material)
async def invoice_material(message: types.Message, state: FSMContext):
    await state.update_data(material=message.text)
    await state.set_state(InvoiceForm.color)
    await message.answer("🎨 *Цвет:*\n\nБелый / Черный / Красный / Другой", parse_mode="Markdown")

@dp.message(InvoiceForm.color)
async def invoice_color(message: types.Message, state: FSMContext):
    await state.update_data(color=message.text)
    await state.set_state(InvoiceForm.quantity)
    await message.answer("🔢 *Количество деталей:*\n\nВведите число", parse_mode="Markdown")

@dp.message(InvoiceForm.quantity)
async def invoice_quantity(message: types.Message, state: FSMContext):
    try:
        quantity = int(message.text)
        await state.update_data(quantity=quantity)
        await state.set_state(InvoiceForm.discount)
        await message.answer(
            "🎁 *Скидка:*\n\n"
            "Введите размер скидки (в %):\n"
            "0 - без скидки",
            parse_mode="Markdown"
        )
    except:
        await message.answer("❌ Введите число")

@dp.message(InvoiceForm.discount)
async def invoice_discount(message: types.Message, state: FSMContext):
    try:
        discount = int(message.text)
        await state.update_data(discount=discount)
        await state.set_state(InvoiceForm.delivery_price)
        await message.answer(
            "🚚 *Стоимость доставки:*\n\n"
            "0 - самовывоз\n"
            "300 - Почта\n"
            "500 - СДЭК",
            parse_mode="Markdown"
        )
    except:
        await message.answer("❌ Введите число")

@dp.message(InvoiceForm.delivery_price)
async def invoice_delivery_price(message: types.Message, state: FSMContext):
    try:
        delivery_price = int(message.text)
        await state.update_data(delivery_price=delivery_price)
        await state.set_state(InvoiceForm.delivery_address)
        
        if delivery_price == 0:
            await state.update_data(delivery_address="Самовывоз")
            await state.set_state(InvoiceForm.payment_method)
            await message.answer(
                "💳 *Способ оплаты:*\n\n"
                "Напишите способ оплаты:\n"
                "Карта / СБП / Наличные",
                parse_mode="Markdown"
            )
        else:
            await message.answer("📍 *Адрес доставки:*\n\nВведите полный адрес", parse_mode="Markdown")
    except:
        await message.answer("❌ Введите число")

@dp.message(InvoiceForm.delivery_address)
async def invoice_address(message: types.Message, state: FSMContext):
    await state.update_data(delivery_address=message.text)
    await state.set_state(InvoiceForm.payment_method)
    await message.answer(
        "💳 *Способ оплаты:*\n\n"
        "Напишите способ оплаты:\n"
        "Карта / СБП / Наличные",
        parse_mode="Markdown"
    )

@dp.message(InvoiceForm.payment_method)
async def invoice_payment_method(message: types.Message, state: FSMContext):
    await state.update_data(payment_method=message.text)
    await state.set_state(InvoiceForm.tracking_number)
    await message.answer(
        "📦 *Трек-номер (опционально):*\n\n"
        "Введите трек-номер или напишите 'пропустить'",
        parse_mode="Markdown"
    )

@dp.message(InvoiceForm.tracking_number)
async def invoice_tracking(message: types.Message, state: FSMContext):
    tracking = None if message.text.lower() == "пропустить" else message.text
    await state.update_data(tracking_number=tracking)
    await state.set_state(InvoiceForm.ready_days)
    await message.answer(
        "⏱ *Срок готовности:*\n\n"
        "Через сколько дней заказ будет готов?\n"
        "Пример: 3 дня",
        parse_mode="Markdown"
    )

@dp.message(InvoiceForm.ready_days)
async def invoice_ready(message: types.Message, state: FSMContext):
    await state.update_data(ready_days=message.text)
    await state.set_state(InvoiceForm.future_promo)
    await message.answer(
        "🎟 *Промокод на будущее (опционально):*\n\n"
        "Введите промокод для следующего заказа или 'пропустить'",
        parse_mode="Markdown"
    )

@dp.message(InvoiceForm.future_promo)
async def invoice_future_promo(message: types.Message, state: FSMContext):
    promo = None if message.text.lower() == "пропустить" else message.text
    await state.update_data(future_promo=promo)
    await state.set_state(InvoiceForm.comment)
    await message.answer(
        "📝 *Комментарий (опционально):*\n\n"
        "Напишите комментарий или 'пропустить'",
        parse_mode="Markdown"
    )

@dp.message(InvoiceForm.comment)
async def invoice_comment(message: types.Message, state: FSMContext):
    comment = None if message.text.lower() == "пропустить" else message.text
    await state.update_data(comment=comment)
    
    data = await state.get_data()
    orders = load_json(ORDERS_FILE)
    order = orders.get(data["order_id"], {})
    
    # Предпросмотр
    preview = f"""
📋 *ПРЕДПРОСМОТР КВИТАНЦИИ*

💰 Стоимость: {data['price']} ₽
🖨️ Материал: {data['material']}
🎨 Цвет: {data['color']}
🔢 Количество: {data['quantity']} шт.
🎁 Скидка: {data['discount']}%
🚚 Доставка: {data['delivery_price']} ₽
📍 Адрес: {data['delivery_address']}
💳 Оплата: {data['payment_method']}
📦 Трек-номер: {data['tracking_number'] or 'Нет'}
⏱ Срок: {data['ready_days']}
🎟 Промокод: {data['future_promo'] or 'Нет'}

👤 Клиент: {order.get('name')}
🆔 Username: @{order.get('username', 'Нет')}

⚠️ Данная квитанция не является фискальным чеком
    """
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Отправить квитанцию", callback_data="send_invoice_confirm")],
        [InlineKeyboardButton(text="🔄 Заполнить заново", callback_data="invoice_restart")]
    ])
    
    await state.set_state(InvoiceForm.confirm)
    await message.answer(preview, parse_mode="Markdown", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data == "send_invoice_confirm")
async def send_invoice(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    orders = load_json(ORDERS_FILE)
    order = orders.get(data["order_id"], {})
    
    payment_data = {
        "price": data["price"],
        "material": data["material"],
        "color": data["color"],
        "quantity": data["quantity"],
        "discount": data["discount"],
        "delivery_price": data["delivery_price"],
        "delivery_address": data["delivery_address"],
        "payment_method": data["payment_method"],
        "tracking_number": data.get("tracking_number"),
        "ready_days": data.get("ready_days"),
        "future_promo": data.get("future_promo"),
        "comment": data.get("comment"),
        "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "inn": "1234567890",
        "ogrnip": "123456789012345"
    }
    
    # Обновляем заказ
    orders[data["order_id"]]["price"] = data["price"]
    final_price = data["price"] * (100 - data["discount"]) / 100 + data["delivery_price"]
    orders[data["order_id"]]["final_price"] = final_price
    orders[data["order_id"]]["status"] = "accepted"
    orders[data["order_id"]]["tracking_number"] = data.get("tracking_number")
    save_json(ORDERS_FILE, orders)
    
    # Генерируем квитанцию
    invoice_img = await generate_invoice(order, payment_data)
    
    # Отправляем пользователю
    await bot.send_photo(
        order["user_id"],
        types.BufferedInputFile(invoice_img.getvalue(), filename=f"invoice_{data['order_id']}.png"),
        caption=f"📋 *КВИТАНЦИЯ ОБ ОПЛАТЕ*\n\n"
                f"🆔 Заказ: `{data['order_id']}`\n"
                f"💰 Сумма к оплате: {final_price:.2f} ₽\n\n"
                f"💳 *Реквизиты для оплаты:*\n"
                f"Карта: **** 1234\n"
                f"Получатель: Иван Иванов\n"
                f"Сумма: {final_price:.2f} ₽\n\n"
                f"✅ После оплаты пришлите скриншот\n"
                f"⚠️ Данная квитанция не является фискальным чеком",
        parse_mode="Markdown"
    )
    
    await callback.message.answer(f"✅ Квитанция отправлена пользователю @{order.get('username', order['name'])}")
    await state.clear()
    await callback.answer()

@dp.callback_query(lambda c: c.data == "invoice_restart")
async def restart_invoice(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("🔄 Начинаем заполнение квитанции заново...")
    await callback.message.answer("💰 Введите стоимость:")
    await callback.answer()

# ========== ОСТАЛЬНЫЕ АДМИН-ФУНКЦИИ ==========
@dp.message(F.text == "📊 Статистика")
async def admin_stats(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    orders = load_json(ORDERS_FILE)
    users = load_json(USERS_FILE)
    reviews = load_json(REVIEWS_FILE)
    
    total_orders = len(orders)
    completed_orders = len([o for o in orders.values() if o.get("status") == "completed"])
    total_users = len(users)
    avg_rating = sum([r["rating"] for r in reviews.values()]) / len(reviews) if reviews else 0
    total_revenue = sum([o.get("price", 0) for o in orders.values() if o.get("price")])
    
    text = f"""
📊 *СТАТИСТИКА БОТА*

👥 Пользователей: {total_users}
📦 Всего заказов: {total_orders}
✅ Завершено: {completed_orders}
⭐ Средний рейтинг: {avg_rating:.1f}/5
💰 Выручка: {total_revenue}₽
    """
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
    await message.answer("📊 *Выберите период*", parse_mode="Markdown", reply_markup=keyboard)

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
    
    text = f"📊 *Отчет за {period_name}*\n\n📦 Заказов: {total_orders}\n💰 Выручка: {total_revenue}₽\n💵 Средний чек: {avg_price:.0f}₽"
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()

@dp.message(F.text == "💰 Запросы скидок")
async def view_discount_requests(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    requests = load_json(DISCOUNT_REQUESTS_FILE)
    pending = {k: v for k, v in requests.items() if v.get("status") == "pending"}
    
    if not pending:
        await message.answer("❌ Нет активных запросов")
        return
    
    text = "💰 *Запросы на скидку:*\n\n"
    for req in list(pending.values())[:10]:
        text += f"👤 @{req.get('username', 'Нет')}\n📝 {req.get('reason', '')[:100]}\n\n"
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
        text += f"👤 @{review.get('username', 'Нет')}\n⭐ {review.get('rating', 0)}/5\n📝 {review.get('text', '')[:100]}\n\n"
    await message.answer(text, parse_mode="Markdown")

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
        text += f"🔹 *{order.get('order_id', 'Нет')}*\n   👤 {order.get('name')}\n   📊 {ORDER_STATUSES.get(order.get('status'), 'new')}\n   💰 {order.get('price', '?')}₽\n\n"
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text == "👥 Пользователи")
async def list_users(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    users = load_json(USERS_FILE)
    text = "👥 *Пользователи:*\n\n"
    for user in list(users.values())[-20:]:
        text += f"👤 @{user.get('username', 'Нет')}\n   📦 Заказов: {user.get('total_orders', 0)}\n   💰 Потрачено: {user.get('total_spent', 0)}₽\n\n"
    await message.answer(text, parse_mode="Markdown")

@dp.message(F.text == "🔄 Изменить статус")
async def change_status_menu(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    orders = load_json(ORDERS_FILE)
    keyboard = []
    for order_id, order in list(orders.items())[-10:]:
        keyboard.append([InlineKeyboardButton(
            text=f"#{order.get('order_id', order_id)}",
            callback_data=f"select_order_status_{order_id}"
        )])
    
    await message.answer("📦 *Выберите заказ:*", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@dp.callback_query(lambda c: c.data.startswith("select_order_status_"))
async def select_order_for_status(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Только для админа")
        return
    
    order_id = callback.data.split("_")[3]
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Принят", callback_data=f"set_status_{order_id}_accepted")],
        [InlineKeyboardButton(text="🔧 В работе", callback_data=f"set_status_{order_id}_in_progress")],
        [InlineKeyboardButton(text="⚡ Почти готов", callback_data=f"set_status_{order_id}_almost_ready")],
        [InlineKeyboardButton(text="🎉 Готов", callback_data=f"set_status_{order_id}_ready")],
        [InlineKeyboardButton(text="🏁 Завершен", callback_data=f"set_status_{order_id}_completed")]
    ])
    
    await callback.message.edit_text(f"🎯 *Новый статус для {order_id}:*", reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("set_status_"))
async def set_order_status(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Только для админа")
        return
    
    _, _, order_id, status = callback.data.split("_")
    orders = load_json(ORDERS_FILE)
    
    if order_id in orders:
        old_status = orders[order_id].get("status", "new")
        orders[order_id]["status"] = status
        save_json(ORDERS_FILE, orders)
        
        status_text = ORDER_STATUSES.get(status, status)
        await bot.send_message(
            orders[order_id]["user_id"],
            f"🔄 *Статус заказа обновлен!*\n\n📦 Заказ: {order_id}\n📊 Новый статус: {status_text}",
            parse_mode="Markdown"
        )
        
        if status == "completed":
            users = load_json(USERS_FILE)
            user_id = str(orders[order_id]["user_id"])
            if user_id in users:
                users[user_id]["total_orders"] = users[user_id].get("total_orders", 0) + 1
                users[user_id]["total_spent"] = users[user_id].get("total_spent", 0) + orders[order_id].get("price", 0)
                save_json(USERS_FILE, users)
        
        await callback.message.edit_text(f"✅ Статус {order_id} изменен на {status_text}")
    await callback.answer()

# ========== ОСНОВНАЯ ЗАЯВКА ==========
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
    await callback.message.edit_text("✅ *Условия приняты!* Продолжаем оформление.", parse_mode="Markdown")
    await state.set_state(OrderForm.name)
    await callback.message.answer("🔹 *Как вас зовут?*", reply_markup=cancel_kb, parse_mode="Markdown")
    await callback.answer()

@dp.message(F.text == "❌ Отмена")
async def cancel_order(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Отменено.", reply_markup=main_menu if message.from_user.id != ADMIN_ID else admin_menu)

@dp.message(OrderForm.name)
async def get_name(message: types.Message, state: FSMContext):
    if len(message.text) < 2:
        await message.answer("❌ Введите корректное имя")
        return
    await state.update_data(name=message.text)
    await state.set_state(OrderForm.contact)
    await message.answer("🔹 *Контакты для связи:*", reply_markup=cancel_kb, parse_mode="Markdown")

@dp.message(OrderForm.contact)
async def get_contact(message: types.Message, state: FSMContext):
    contact = message.text.strip()
    if contact.lower() == "пропустить":
        contact = f"Telegram: @{message.from_user.username}" if message.from_user.username else f"ID: {message.from_user.id}"
    await state.update_data(contact=contact)
    await state.set_state(OrderForm.delivery)
    await message.answer("🔹 *Способ получения:*", reply_markup=delivery_kb, parse_mode="Markdown")

@dp.message(OrderForm.delivery)
async def get_delivery(message: types.Message, state: FSMContext):
    if "Самовывоз" in message.text:
        delivery = "🚗 Самовывоз"
    elif "Почта" in message.text:
        delivery = "📦 Почта России"
    elif "СДЭК" in message.text:
        delivery = "🚚 СДЭК"
    else:
        await message.answer("❌ Выберите из кнопок")
        return
    
    await state.update_data(delivery=delivery)
    await state.set_state(OrderForm.promo)
    await message.answer("🎟 *Промокод* (или 'пропустить'):", reply_markup=cancel_kb, parse_mode="Markdown")

@dp.message(OrderForm.promo)
async def get_promo(message: types.Message, state: FSMContext):
    promo = None if message.text.lower() == "пропустить" else message.text.upper()
    if promo:
        promocodes = load_json(PROMOCODES_FILE)
        if promo in promocodes and not promocodes[promo]["used"]:
            await state.update_data(promo=promo)
            await message.answer(f"✅ Промокод {promo} активирован!")
        else:
            await message.answer("❌ Неверный промокод")
            await state.update_data(promo=None)
    else:
        await state.update_data(promo=None)
    
    await state.set_state(OrderForm.model_type)
    await message.answer("🔹 *У вас есть готовая модель?*", reply_markup=model_type_kb, parse_mode="Markdown")

@dp.message(OrderForm.model_type)
async def get_model_type(message: types.Message, state: FSMContext):
    if "готовая модель" in message.text:
        await state.update_data(model_type="ready", files=[])
        await state.set_state(OrderForm.waiting_files)
        await message.answer("📁 *Отправьте файлы STL/OBJ/3MF*\nКогда закончите - напишите 'готово'", reply_markup=cancel_kb, parse_mode="Markdown")
    elif "сделать модель" in message.text:
        await state.update_data(model_type="need_design", files=[])
        await state.set_state(OrderForm.description)
        await message.answer("🎨 *Опишите, что нужно смоделировать:*", reply_markup=cancel_kb, parse_mode="Markdown")
    else:
        await message.answer("❌ Выберите из кнопок")

@dp.message(OrderForm.waiting_files)
async def get_files(message: types.Message, state: FSMContext):
    data = await state.get_data()
    files = data.get("files", [])
    
    if message.document:
        file_name = message.document.file_name
        ext = file_name.split('.')[-1].lower() if '.' in file_name else ''
        if ext in ['stl', 'obj', '3mf']:
            files.append({"file_id": message.document.file_id, "name": file_name})
            await state.update_data(files=files)
            await message.answer(f"✅ Добавлен {file_name}\nВсего: {len(files)}")
        else:
            await message.answer("❌ Неподдерживаемый формат")
    elif message.text and message.text.lower() == "готово":
        if not files:
            await message.answer("❌ Отправьте хотя бы один файл")
            return
        await state.set_state(OrderForm.description)
        await message.answer("📝 *Пожелания по печати:*", reply_markup=cancel_kb, parse_mode="Markdown")
    else:
        await message.answer("Отправьте файл или напишите 'готово'")

@dp.message(OrderForm.description)
async def get_description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    data = await state.get_data()
    order_id = generate_order_id()
    
    order = {
        "order_id": order_id,
        "user_id": message.from_user.id,
        "username": message.from_user.username,
        "name": data["name"],
        "contact": data["contact"],
        "delivery": data["delivery"],
        "promocode": data.get("promo"),
        "model_type": data["model_type"],
        "files": data.get("files", []),
        "description": data["description"],
        "status": "new",
        "created_at": str(datetime.now())
    }
    
    orders = load_json(ORDERS_FILE)
    orders[order_id] = order
    save_json(ORDERS_FILE, orders)
    
    await message.answer(f"✅ *Заявка отправлена!*\n🆔 Номер: `{order_id}`\n\nСтатус можно проверить /status", parse_mode="Markdown")
    
    if ADMIN_ID:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Создать квитанцию", callback_data=f"create_invoice_{order_id}")]
        ])
        await bot.send_message(ADMIN_ID, f"🔔 *Новая заявка!*\n👤 {data['name']}\n🆔 {order_id}", reply_markup=kb)
    
    await state.clear()

# ========== ВЕБ-СЕРВЕР ==========
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
    print(f"✅ Веб-сервер на порту {port}")

# ========== ЗАПУСК ==========
async def main():
    await start_web_server()
    print("🚀 Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
