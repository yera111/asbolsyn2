import asyncio
import logging
import datetime
import math
import json
from decimal import Decimal
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.types import (
    Message, CallbackQuery, ReplyKeyboardMarkup, 
    KeyboardButton, ReplyKeyboardRemove, ContentType
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from .config import (
    BOT_TOKEN, ADMIN_CHAT_ID, ALMATY_TIMEZONE, 
    RATE_LIMIT_GENERAL, RATE_LIMIT_REGISTER, RATE_LIMIT_ADD_MEAL, RATE_LIMIT_PAYMENT,
    TELEGRAM_PAYMENT_PROVIDER_TOKEN, TELEGRAM_PAYMENT_CURRENCY, TELEGRAM_PAYMENT_ENABLED
)
from .db import init_db, close_db
from .models import Consumer, Vendor, VendorStatus, Meal, Order, OrderStatus, Metric, MetricType
from .tasks import scheduled_tasks
from .metrics import track_metric, get_metrics_report, get_metrics_dashboard_data
from .security import rate_limit
from .payment import payment_gateway

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher with FSM storage
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Timezone utility functions
def get_current_almaty_time():
    """Get current time in Almaty timezone"""
    return datetime.datetime.now(ALMATY_TIMEZONE)

def to_almaty_time(dt):
    """Convert any datetime to Almaty timezone"""
    if dt.tzinfo is None:
        # Make timezone-aware with UTC
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt.astimezone(ALMATY_TIMEZONE)

def ensure_timezone_aware(dt):
    """Ensure a datetime is timezone-aware, assuming Almaty timezone if naive"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=ALMATY_TIMEZONE)
    return dt

def format_pickup_time(dt):
    """Format a datetime for display, ensuring it's in Almaty timezone"""
    if dt is None:
        return None
    # First make sure the datetime is timezone-aware
    dt = ensure_timezone_aware(dt)
    # Then explicitly convert to Almaty timezone
    dt = to_almaty_time(dt)
    # Log for debugging
    logging.info(f"Formatting time: {dt} (with tzinfo: {dt.tzinfo})")
    return dt.strftime("%d.%m.%Y %H:%M")

async def save_order_with_timezone(order):
    """Save an order, ensuring all datetime fields are timezone-aware"""
    # Make all datetime fields timezone-aware
    order.created_at = ensure_timezone_aware(order.created_at)
    order.completed_at = ensure_timezone_aware(order.completed_at)
    order.pickup_confirmed_at = ensure_timezone_aware(order.pickup_confirmed_at)
    await order.save()

# Russian text templates
TEXT = {
    "welcome": "Добро пожаловать в As Bolsyn! Этот бот поможет вам найти и приобрести блюда от местных заведений по сниженным ценам.",
    "help": "Доступные команды:\n/start - Запустить бот\n/help - Показать эту справку\n/register_vendor - Зарегистрироваться как поставщик\n/add_meal - Добавить блюдо (только для поставщиков)\n/my_meals - Просмотреть мои блюда (только для поставщиков)\n/browse_meals - Просмотреть доступные блюда\n/meals_nearby - Найти блюда поблизости\n/view_meal ID - Посмотреть детали блюда\n/my_orders - Просмотреть мои заказы\n/vendor_orders - Просмотреть заказы на мои блюда (только для поставщиков)\n/complete_order ID - Подтвердить выдачу заказа (только для поставщиков)\n/cancel_order ID - Отменить застрявший заказ (только для администраторов)",
    "vendor_register_start": "Начинаем процесс регистрации поставщика. Пожалуйста, укажите название вашего заведения:",
    "vendor_ask_phone": "Спасибо! Теперь укажите контактный телефон:",
    "vendor_registered": "Ваша заявка на регистрацию поставщика отправлена на рассмотрение. Мы свяжемся с вами в ближайшее время.",
    "vendor_already_registered": "Вы уже зарегистрированы как поставщик. Статус вашей заявки: {status}",
    "admin_new_vendor": "Новая заявка на регистрацию поставщика!\n\nID: {telegram_id}\nНазвание: {name}\nТелефон: {phone}\n\nДля подтверждения используйте команду:\n/approve_vendor {telegram_id}\n\nДля отклонения используйте команду:\n/reject_vendor {telegram_id}",
    "admin_approved_vendor": "Поставщик {name} (ID: {telegram_id}) был успешно одобрен.",
    "admin_rejected_vendor": "Поставщик {name} (ID: {telegram_id}) был отклонен.",
    "vendor_approved": "Поздравляем! Ваша заявка на регистрацию поставщика была одобрена. Теперь вы можете добавлять блюда.",
    "vendor_rejected": "К сожалению, ваша заявка на регистрацию поставщика была отклонена.",
    "not_admin": "У вас нет прав администратора для выполнения этой команды.",
    "vendor_not_found": "Поставщик с ID {telegram_id} не найден.",
    "not_vendor": "Эта команда доступна только для зарегистрированных поставщиков.",
    "vendor_not_approved": "Ваша заявка еще не была одобрена администратором. Пожалуйста, дождитесь одобрения.",
    "meal_add_start": "Начинаем процесс добавления блюда. Пожалуйста, укажите название блюда:",
    "meal_ask_description": "Теперь добавьте описание блюда:",
    "meal_ask_price": "Укажите цену блюда в тенге (только число):",
    "meal_invalid_price": "Пожалуйста, укажите цену в числовом формате (например, 1500).",
    "meal_ask_quantity": "Укажите количество порций:",
    "meal_invalid_quantity": "Пожалуйста, укажите количество порций в виде целого числа.",
    "meal_ask_pickup_start": "Укажите время начала самовывоза в формате ЧЧ:ММ:",
    "meal_invalid_time_format": "Неверный формат времени. Пожалуйста, используйте формат ЧЧ:ММ (например, 18:30).",
    "meal_ask_pickup_end": "Укажите время окончания самовывоза в формате ЧЧ:ММ:",
    "meal_ask_location_address": "Укажите адрес места самовывоза:",
    "meal_ask_location_coords": "Теперь, пожалуйста, отправьте точную геолокацию места самовывоза, используя функцию Telegram 'Отправить геопозицию':",
    "meal_invalid_location": "Не удалось получить координаты. Пожалуйста, воспользуйтесь функцией Telegram 'Отправить геопозицию'.",
    "meal_added_success": "Блюдо успешно добавлено!\n\nНазвание: {name}\nОписание: {description}\nЦена: {price} тенге\nКоличество: {quantity} порций\nВремя самовывоза: {pickup_start} - {pickup_end}\nАдрес: {address}",
    "my_meals_empty": "У вас пока нет добавленных блюд. Используйте команду /add_meal, чтобы добавить блюдо.",
    "my_meals_list_header": "Ваши блюда:\n",
    "my_meals_item": "{id}. {name} - {price} тенге, {quantity} порций, время: {pickup_start}-{pickup_end}",
    "meal_delete_success": "Блюдо успешно удалено.",
    "meal_not_found": "Блюдо не найдено.",
    "browse_meals_header": "Доступные блюда:\n",
    "browse_meals_item": "{id}. {name} - {price} тенге\nПоставщик: {vendor}\nКоличество: {quantity} порций\nВремя самовывоза: {pickup_start} - {pickup_end}",
    "browse_meals_empty": "В данный момент нет доступных блюд. Пожалуйста, проверьте позже.",
    "meals_nearby_prompt": "Для поиска блюд поблизости, пожалуйста, поделитесь своей геопозицией, используя функцию Telegram 'Отправить геопозицию':",
    "meals_nearby_header": "Ближайшие блюда к вам:\n",
    "meals_nearby_item": "{id}. {name} - {price} тенге, {distance:.1f} км\nПоставщик: {vendor}\nКоличество: {quantity} порций\nВремя самовывоза: {pickup_start} - {pickup_end}",
    "meals_nearby_empty": "Рядом с вами нет доступных блюд в радиусе {radius} км. Пожалуйста, попробуйте позже или увеличьте радиус поиска.",
    "meal_details_header": "Информация о блюде:\n",
    "meal_details": "Название: {name}\nОписание: {description}\nЦена: {price} тенге\nПоставщик: {vendor}\nКоличество: {quantity} порций\nВремя самовывоза: {pickup_start} - {pickup_end}\nАдрес: {address}",
    "meal_view_button": "Купить",
    "meal_id_invalid": "Неверный ID блюда. Пожалуйста, используйте числовой ID.",
    "select_portions": "Выберите количество порций для заказа:",
    "portion_selection": "Вы выбрали {count} порций блюда \"{name}\".\nОбщая стоимость: {total_price} тенге.",
    "view_meal_button": "Посмотреть",
    "order_created": "Заказ #{order_id} создан!\n\nБлюдо: {meal_name}\nКоличество: {quantity} порций\nЦена: {price} тенге\n\nОплатите заказ, нажав на кнопку ниже.",
    "order_payment_button": "Оплатить",
    "order_confirmed": "Заказ #{order_id} успешно оплачен!\n\nБлюдо: {meal_name}\nКоличество: {quantity} порций\nПоставщик: {vendor_name}\nАдрес: {address}\nВремя самовывоза: с {pickup_start} до {pickup_end}\n\nПокажите этот чек продавцу при получении.",
    "vendor_notification": "Новый оплаченный заказ #{order_id}!\n\nБлюдо: {meal_name}\nКоличество: {quantity} порций\nВремя самовывоза: с {pickup_start} до {pickup_end}",
    "order_mark_completed": "Заказ #{order_id} успешно отмечен как выполненный!",
    "order_complete_usage": "Используйте формат: /complete_order <id_заказа>",
    "order_complete_not_paid": "Статус заказа должен быть «Оплачен», чтобы подтвердить выдачу.",
    "order_cancel_success": "Заказ #{order_id} был успешно отменен.",
    "order_cancel_usage": "Используйте формат: /cancel_order <id_заказа>",
    "order_not_found": "Заказ #{order_id} не найден.",
    # Payment related texts
    "payment_not_available": "В данный момент оплата недоступна. Пожалуйста, попробуйте позже или обратитесь в поддержку.",
    "payment_title": "Заказ блюда в As Bolsyn",
    "payment_description": "Блюдо: {meal_name}\nКоличество: {count} порций",
    "payment_payload": "order_{order_id}",
    "payment_successful": "Оплата успешно произведена! Ваш заказ #{order_id} оформлен.",
    "payment_checkout_failed": "Не удалось обработать платеж. Пожалуйста, попробуйте еще раз или выберите другой способ оплаты."
}


# Define states for vendor registration
class VendorRegistration(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()


# Define states for meal creation
class MealCreation(StatesGroup):
    waiting_for_name = State()
    waiting_for_description = State()
    waiting_for_price = State()
    waiting_for_quantity = State()
    waiting_for_pickup_start = State()
    waiting_for_pickup_end = State()
    waiting_for_location_address = State()
    waiting_for_location_coords = State()


# Define states for nearby meals search
class MealsNearbySearch(StatesGroup):
    waiting_for_location = State()


# Define states for portion selection
class PortionSelection(StatesGroup):
    waiting_for_quantity = State()


# Define state for order tracking
class OrderTracking(StatesGroup):
    waiting_for_order_id = State()


# Helper function to get the main menu keyboard
def get_main_keyboard():
    """Returns the main menu keyboard markup with additional orders button"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Просмотреть блюда"), KeyboardButton(text="📍 Блюда поблизости")],
            [KeyboardButton(text="🛒 Мои заказы"), KeyboardButton(text="🏪 Зарегистрироваться как поставщик")],
            [KeyboardButton(text="❓ Помощь")]
        ],
        resize_keyboard=True
    )


@dp.message(Command("start"))
@rate_limit(limit=RATE_LIMIT_GENERAL, period=60, key="start_command")
async def cmd_start(message: Message):
    """Handler for /start command"""
    # Register user if not already registered
    user_id = message.from_user.id
    consumer, created = await Consumer.get_or_create(telegram_id=user_id)
    
    # Track user registration if this is a new user
    if created:
        await track_metric(
            metric_type=MetricType.USER_REGISTRATION,
            user_id=user_id
        )
    
    # Get the main keyboard
    keyboard = get_main_keyboard()
    
    # Combine welcome message with usage instructions
    welcome_text = (
        f"{TEXT['welcome']}\n\n"
        "Что вы можете сделать:\n"
        "• Просмотреть доступные блюда\n"
        "• Найти блюда рядом с вами\n"
        "• Зарегистрироваться как поставщик питания\n\n"
        "Выберите опцию из меню ниже или используйте команды бота:"
    )
    
    await message.answer(welcome_text, reply_markup=keyboard)


@dp.message(Command("help"))
@rate_limit(limit=RATE_LIMIT_GENERAL, period=60, key="help_command")
async def cmd_help(message: Message):
    """Handler for /help command"""
    await message.answer(TEXT["help"], reply_markup=get_main_keyboard())


@dp.message(Command("register_vendor"))
@rate_limit(limit=RATE_LIMIT_REGISTER, period=60, key="register_vendor_command")
async def cmd_register_vendor(message: Message, state: FSMContext):
    """Handler to start vendor registration process"""
    user_id = message.from_user.id
    
    # Check if already registered
    existing_vendor = await Vendor.filter(telegram_id=user_id).first()
    if existing_vendor:
        await message.answer(TEXT["vendor_already_registered"].format(status=existing_vendor.status.value), reply_markup=get_main_keyboard())
        return
    
    # Start registration process
    await state.set_state(VendorRegistration.waiting_for_name)
    await message.answer(TEXT["vendor_register_start"])


@dp.message(VendorRegistration.waiting_for_name)
async def process_vendor_name(message: Message, state: FSMContext):
    """Handler to process vendor name input"""
    # Save the vendor name
    await state.update_data(name=message.text)
    
    # Move to the next step
    await state.set_state(VendorRegistration.waiting_for_phone)
    await message.answer(TEXT["vendor_ask_phone"])


@dp.message(VendorRegistration.waiting_for_phone)
async def process_vendor_phone(message: Message, state: FSMContext):
    """Handler to process vendor phone input and complete registration"""
    user_id = message.from_user.id
    
    # Get the data from previous steps
    data = await state.get_data()
    vendor_name = data.get("name")
    
    # Save the vendor in database
    vendor = await Vendor.create(
        telegram_id=user_id,
        name=vendor_name,
        contact_phone=message.text,
        status=VendorStatus.PENDING
    )
    
    # Track vendor registration metric
    await track_metric(
        metric_type=MetricType.VENDOR_REGISTRATION,
        user_id=user_id,
        entity_id=vendor.id,
        metadata={"vendor_name": vendor_name}
    )
    
    # Clear the state
    await state.clear()
    
    # Notify the vendor
    await message.answer(TEXT["vendor_registered"], reply_markup=get_main_keyboard())
    
    # Notify admin about new vendor registration
    if ADMIN_CHAT_ID:
        await bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=TEXT["admin_new_vendor"].format(
                telegram_id=user_id,
                name=vendor_name,
                phone=message.text
            )
        )


@dp.message(Command("approve_vendor"))
async def cmd_approve_vendor(message: Message):
    """Handler for admin to approve a vendor"""
    # Only admin can approve vendors
    if str(message.from_user.id) != ADMIN_CHAT_ID:
        await message.answer(TEXT["not_admin"])
        return
    
    # Parse vendor ID from command arguments
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Использование: /approve_vendor <telegram_id>")
        return
    
    try:
        vendor_telegram_id = int(args[1])
        
        # Find the vendor
        vendor = await Vendor.filter(telegram_id=vendor_telegram_id).first()
        if not vendor:
            await message.answer(TEXT["vendor_not_found"].format(telegram_id=vendor_telegram_id))
            return
        
        # Update vendor status
        vendor.status = VendorStatus.APPROVED
        await vendor.save()
        
        # Track vendor approval metric
        await track_metric(
            metric_type=MetricType.VENDOR_APPROVAL,
            entity_id=vendor.id,
            user_id=vendor_telegram_id,
            metadata={"vendor_name": vendor.name}
        )
        
        # Notify admin
        await message.answer(TEXT["admin_approved_vendor"].format(name=vendor.name, telegram_id=vendor_telegram_id))
        
        # Notify vendor
        await bot.send_message(
            chat_id=vendor_telegram_id,
            text=TEXT["vendor_approved"]
        )
    
    except ValueError:
        await message.answer("Неверный формат Telegram ID. Используйте число.")
    except Exception as e:
        logging.error(f"Error approving vendor: {e}")
        await message.answer(f"Произошла ошибка при одобрении поставщика: {e}")


@dp.message(Command("reject_vendor"))
async def cmd_reject_vendor(message: Message):
    """Handler for admin to reject a vendor"""
    user_id = message.from_user.id
    
    # Check if user is admin
    if not ADMIN_CHAT_ID or str(user_id) != ADMIN_CHAT_ID:
        await message.answer(TEXT["not_admin"])
        return
    
    # Get vendor ID from command arguments
    command_parts = message.text.split()
    if len(command_parts) != 2:
        await message.answer("Используйте формат: /reject_vendor ID")
        return
    
    try:
        vendor_telegram_id = int(command_parts[1])
        vendor = await Vendor.filter(telegram_id=vendor_telegram_id).first()
        
        if not vendor:
            await message.answer(TEXT["vendor_not_found"].format(telegram_id=vendor_telegram_id))
            return
        
        # Update vendor status
        vendor.status = VendorStatus.REJECTED
        await vendor.save()
        
        # Notify admin about rejection
        await message.answer(TEXT["admin_rejected_vendor"].format(
            telegram_id=vendor_telegram_id,
            name=vendor.name
        ))
        
        # Notify vendor about rejection
        await bot.send_message(
            chat_id=vendor_telegram_id,
            text=TEXT["vendor_rejected"]
        )
    
    except (ValueError, TypeError):
        await message.answer("Неверный формат ID. Используйте числовой ID.")


@dp.message(Command("add_meal"))
@rate_limit(limit=RATE_LIMIT_ADD_MEAL, period=60, key="add_meal_command")
async def cmd_add_meal(message: Message, state: FSMContext):
    """Handler to start meal creation process"""
    user_id = message.from_user.id
    
    # Check if user is a registered vendor
    vendor = await Vendor.filter(telegram_id=user_id).first()
    if not vendor:
        await message.answer(TEXT["not_vendor"])
        return
    
    # Check if vendor is approved
    if vendor.status != VendorStatus.APPROVED:
        await message.answer(TEXT["vendor_not_approved"])
        return
    
    # Start meal creation process
    await state.set_state(MealCreation.waiting_for_name)
    await message.answer(TEXT["meal_add_start"])


@dp.message(MealCreation.waiting_for_name)
async def process_meal_name(message: Message, state: FSMContext):
    """Handler to process meal name input"""
    # Save the meal name
    await state.update_data(name=message.text)
    
    # Move to the next step
    await state.set_state(MealCreation.waiting_for_description)
    await message.answer(TEXT["meal_ask_description"])


@dp.message(MealCreation.waiting_for_description)
async def process_meal_description(message: Message, state: FSMContext):
    """Handler to process meal description input"""
    # Save the meal description
    await state.update_data(description=message.text)
    
    # Move to the next step
    await state.set_state(MealCreation.waiting_for_price)
    await message.answer(TEXT["meal_ask_price"])


@dp.message(MealCreation.waiting_for_price)
async def process_meal_price(message: Message, state: FSMContext):
    """Handler to process meal price input"""
    # Validate price input
    try:
        price = Decimal(message.text.strip())
        if price <= 0:
            raise ValueError("Price must be positive")
            
        # Save the meal price
        await state.update_data(price=float(price))
        
        # Move to the next step
        await state.set_state(MealCreation.waiting_for_quantity)
        await message.answer(TEXT["meal_ask_quantity"])
    except (ValueError, TypeError):
        await message.answer(TEXT["meal_invalid_price"])


@dp.message(MealCreation.waiting_for_quantity)
async def process_meal_quantity(message: Message, state: FSMContext):
    """Handler to process meal quantity input"""
    # Validate quantity input
    try:
        quantity = int(message.text.strip())
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
            
        # Save the meal quantity
        await state.update_data(quantity=quantity)
        
        # Move to the next step
        await state.set_state(MealCreation.waiting_for_pickup_start)
        await message.answer(TEXT["meal_ask_pickup_start"])
    except (ValueError, TypeError):
        await message.answer(TEXT["meal_invalid_quantity"])


@dp.message(MealCreation.waiting_for_pickup_start)
async def process_meal_pickup_start(message: Message, state: FSMContext):
    """Handler to process meal pickup start time input"""
    # Validate time format
    try:
        time_str = message.text.strip()
        hours, minutes = map(int, time_str.split(':'))
        
        if hours < 0 or hours > 23 or minutes < 0 or minutes > 59:
            raise ValueError("Invalid time values")
            
        # Create datetime object for today with the specified time in Almaty timezone
        now = get_current_almaty_time()
        pickup_start = now.replace(hour=hours, minute=minutes, second=0, microsecond=0)
        
        # If the time is in the past, assume it's for tomorrow
        if pickup_start < now:
            pickup_start = pickup_start + datetime.timedelta(days=1)
            
        # Log the time information for debugging
        logging.info(f"Pickup start time: {pickup_start} (Almaty timezone)")
        
        # Save the pickup start time
        await state.update_data(
            pickup_start_str=time_str,
            pickup_start=pickup_start
        )
        
        # Move to the next step
        await state.set_state(MealCreation.waiting_for_pickup_end)
        await message.answer(TEXT["meal_ask_pickup_end"])
    except (ValueError, TypeError):
        await message.answer(TEXT["meal_invalid_time_format"])


@dp.message(MealCreation.waiting_for_pickup_end)
async def process_meal_pickup_end(message: Message, state: FSMContext):
    """Handler to process meal pickup end time input"""
    # Validate time format
    try:
        time_str = message.text.strip()
        hours, minutes = map(int, time_str.split(':'))
        
        if hours < 0 or hours > 23 or minutes < 0 or minutes > 59:
            raise ValueError("Invalid time values")
            
        # Get the pickup start time from state
        data = await state.get_data()
        pickup_start = data.get('pickup_start')
        
        # Create datetime object for today with the specified time in Almaty timezone
        now = get_current_almaty_time()
        pickup_end = now.replace(hour=hours, minute=minutes, second=0, microsecond=0)
        
        # Ensure pickup_end is on the same day as pickup_start initially
        pickup_end = pickup_end.replace(
            year=pickup_start.year,
            month=pickup_start.month,
            day=pickup_start.day
        )
        
        # Ensure end time is after start time
        if pickup_end <= pickup_start:
            # If end time is earlier, assume it's for the next day
            pickup_end = pickup_end + datetime.timedelta(days=1)
        
        # Log the time information for debugging
        logging.info(f"Pickup end time: {pickup_end} (Almaty timezone)")
        logging.info(f"Pickup window: {pickup_start} - {pickup_end}")
        
        # Save the pickup end time
        await state.update_data(
            pickup_end_str=time_str,
            pickup_end=pickup_end
        )
        
        # Move to the next step
        await state.set_state(MealCreation.waiting_for_location_address)
        await message.answer(TEXT["meal_ask_location_address"])
    except (ValueError, TypeError):
        await message.answer(TEXT["meal_invalid_time_format"])


@dp.message(MealCreation.waiting_for_location_address)
async def process_meal_location_address(message: Message, state: FSMContext):
    """Handler to process meal location address input"""
    # Save the location address
    await state.update_data(location_address=message.text)
    
    # Create keyboard with location button
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Отправить геопозицию", request_location=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    # Move to the next step
    await state.set_state(MealCreation.waiting_for_location_coords)
    await message.answer(TEXT["meal_ask_location_coords"], reply_markup=keyboard)


@dp.message(MealCreation.waiting_for_location_coords)
async def process_meal_location_coords(message: Message, state: FSMContext):
    """Handler to process meal location coordinates and complete meal creation"""
    # Check if we received a location
    if not message.location:
        await message.answer(TEXT["meal_invalid_location"])
        return
    
    # Get the latitude and longitude
    latitude = message.location.latitude
    longitude = message.location.longitude
    
    # Get all the data from previous steps
    data = await state.get_data()
    
    # Create Meal object
    vendor = await Vendor.filter(telegram_id=message.from_user.id).first()
    
    # Get the previously stored pickup times
    pickup_start_time = data.get("pickup_start")
    pickup_end_time = data.get("pickup_end")
    
    # Ensure both pickup times are timezone-aware
    pickup_start_time = ensure_timezone_aware(pickup_start_time)
    pickup_end_time = ensure_timezone_aware(pickup_end_time)
    
    # Log the time information for debugging
    logging.info(f"Creating meal with pickup window: {pickup_start_time} - {pickup_end_time}")
    
    # Create meal record
    meal = await Meal.create(
        vendor=vendor,
        name=data.get("name"),
        description=data.get("description"),
        price=data.get("price"),
        quantity=data.get("quantity"),
        pickup_start_time=pickup_start_time,
        pickup_end_time=pickup_end_time,
        location_address=data.get("location_address"),
        location_latitude=latitude,
        location_longitude=longitude,
        is_active=True
    )
    
    # Track meal creation metric
    await track_metric(
        metric_type=MetricType.MEAL_CREATION,
        entity_id=meal.id,
        user_id=message.from_user.id,
        metadata={
            "meal_name": meal.name,
            "price": float(meal.price),
            "quantity": meal.quantity,
            "vendor_id": vendor.id,
            "vendor_name": vendor.name
        }
    )
    
    # Clear the state
    await state.clear()
    
    # Format pickup times
    pickup_start_time = to_almaty_time(ensure_timezone_aware(meal.pickup_start_time))
    pickup_end_time = to_almaty_time(ensure_timezone_aware(meal.pickup_end_time))
    
    # Format for display with proper timezone
    pickup_start_format = pickup_start_time.strftime("%d.%m.%Y %H:%M")
    pickup_end_format = pickup_end_time.strftime("%d.%m.%Y %H:%M")
    
    # Log the formatted times for debugging
    logging.info(f"Meal created with pickup window (Almaty): {pickup_start_format} - {pickup_end_format}")
    
    # Notify the vendor
    await message.answer(
        TEXT["meal_added_success"].format(
            name=meal.name,
            description=meal.description,
            price=meal.price,
            quantity=meal.quantity,
            pickup_start=pickup_start_format,
            pickup_end=pickup_end_format,
            address=meal.location_address
        ),
        reply_markup=get_main_keyboard()
    )


@dp.message(Command("my_meals"))
@rate_limit(limit=RATE_LIMIT_GENERAL, period=60, key="my_meals_command")
async def cmd_my_meals(message: Message):
    """Handler to view vendor's meals"""
    user_id = message.from_user.id
    
    # Check if user is a registered vendor
    vendor = await Vendor.filter(telegram_id=user_id).first()
    if not vendor:
        await message.answer(TEXT["not_vendor"], reply_markup=get_main_keyboard())
        return
    
    # Get all active meals for this vendor
    meals = await Meal.filter(vendor=vendor, is_active=True)
    
    if not meals:
        await message.answer(TEXT["my_meals_empty"], reply_markup=get_main_keyboard())
        return
    
    # Build the meals list message
    response = TEXT["my_meals_list_header"]
    
    for i, meal in enumerate(meals, 1):
        # Format pickup times using format_pickup_time to ensure correct timezone
        pickup_start_time = to_almaty_time(ensure_timezone_aware(meal.pickup_start_time))
        pickup_end_time = to_almaty_time(ensure_timezone_aware(meal.pickup_end_time))
        
        # Format as time only (HH:MM)
        pickup_start = pickup_start_time.strftime("%H:%M")
        pickup_end = pickup_end_time.strftime("%H:%M")
        
        # Log the times for debugging
        logging.info(f"Meal {meal.id}: Pickup window (Almaty time): {pickup_start}-{pickup_end}")
        
        response += TEXT["my_meals_item"].format(
            id=i,
            name=meal.name,
            price=meal.price,
            quantity=meal.quantity,
            pickup_start=pickup_start,
            pickup_end=pickup_end
        ) + "\n"
    
    await message.answer(response, reply_markup=get_main_keyboard())


@dp.message(Command("delete_meal"))
@rate_limit(limit=RATE_LIMIT_GENERAL, period=60, key="delete_meal_command")
async def cmd_delete_meal(message: Message):
    """Handler for vendor to delete a meal"""
    user_id = message.from_user.id
    
    # Check if user is a registered vendor
    vendor = await Vendor.filter(telegram_id=user_id).first()
    if not vendor:
        await message.answer(TEXT["not_vendor"], reply_markup=get_main_keyboard())
        return
    
    # Get meal ID from command arguments
    command_parts = message.text.split()
    if len(command_parts) != 2:
        await message.answer("Используйте формат: /delete_meal ID", reply_markup=get_main_keyboard())
        return
    
    try:
        meal_id = int(command_parts[1])
        
        # Find the meal, ensuring it belongs to this vendor
        meal = await Meal.filter(id=meal_id, vendor=vendor, is_active=True).first()
        
        if not meal:
            await message.answer(TEXT["meal_not_found"], reply_markup=get_main_keyboard())
            return
        
        # Deactivate the meal (soft delete)
        meal.is_active = False
        await meal.save()
        
        # Notify vendor
        await message.answer(TEXT["meal_delete_success"], reply_markup=get_main_keyboard())
    
    except (ValueError, TypeError):
        await message.answer("Неверный формат ID. Используйте числовой ID блюда.", reply_markup=get_main_keyboard())


@dp.message(Command("browse_meals"))
@rate_limit(limit=RATE_LIMIT_GENERAL, period=60, key="browse_meals_command")
async def cmd_browse_meals(message: Message):
    """Handler for /browse_meals command"""
    user_id = message.from_user.id
    
    # Register user if not already registered
    consumer, created = await Consumer.get_or_create(telegram_id=user_id)
    
    # Track browse meals event
    await track_metric(
        metric_type=MetricType.MEAL_BROWSE,
        user_id=user_id
    )
    
    # Get all active meals with quantity > 0
    # Use the current time in Almaty timezone for filtering
    current_time = get_current_almaty_time()
    logging.info(f"Current Almaty time for meal filtering: {current_time}")
    
    # Get all meals first, then filter in memory to ensure proper timezone handling
    all_meals = await Meal.filter(is_active=True, quantity__gt=0).prefetch_related('vendor').order_by('-created_at')
    
    # Filter meals in memory to ensure proper timezone handling
    meals = []
    for meal in all_meals:
        # Ensure end time is timezone-aware and in Almaty timezone
        pickup_end_time = ensure_timezone_aware(meal.pickup_end_time)
        if pickup_end_time > current_time:
            meals.append(meal)
            logging.info(f"Including meal: {meal.name}, end time: {pickup_end_time}")
        else:
            logging.info(f"Excluding meal: {meal.name}, end time: {pickup_end_time} (already passed)")
    
    if not meals:
        await message.answer(TEXT["browse_meals_empty"], reply_markup=get_main_keyboard())
        return
    
    # Send a response for each meal to allow individual buttons
    for meal in meals:
        # Create inline keyboard with View button
        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(
                    text=TEXT["view_meal_button"], 
                    callback_data=f"view_meal:{meal.id}"
                )]
            ]
        )
        
        # Format pickup times
        pickup_start = format_pickup_time(meal.pickup_start_time)
        pickup_end = format_pickup_time(meal.pickup_end_time)
        
        # Send message with meal details and View button
        await message.answer(
            TEXT["browse_meals_item"].format(
                id=meal.id,
                name=meal.name,
                price=meal.price,
                vendor=meal.vendor.name,
                quantity=meal.quantity,
                pickup_start=pickup_start,
                pickup_end=pickup_end
            ),
            reply_markup=keyboard
        )


@dp.callback_query(lambda c: c.data and c.data.startswith('view_meal:'))
async def callback_view_meal(callback_query: CallbackQuery):
    """Handler for 'View' button callback for a specific meal"""
    # Register user if not already registered
    user_id = callback_query.from_user.id
    consumer, created = await Consumer.get_or_create(telegram_id=user_id)
    
    # Extract meal ID from callback data
    meal_id = int(callback_query.data.split(':', 1)[1])
    
    # Get the meal
    meal = await Meal.filter(id=meal_id, is_active=True).prefetch_related('vendor').first()
    
    if not meal:
        await callback_query.answer(TEXT["meal_not_found"])
        return
    
    # Track meal view metric
    await track_metric(
        metric_type=MetricType.MEAL_VIEW,
        entity_id=meal.id,
        user_id=user_id,
        metadata={
            "meal_name": meal.name,
            "price": float(meal.price),
            "vendor_name": meal.vendor.name
        }
    )
    
    # Format pickup times
    pickup_start = format_pickup_time(meal.pickup_start_time)
    pickup_end = format_pickup_time(meal.pickup_end_time)
    
    # Create options for selecting number of portions
    portion_buttons = []
    max_portions = min(5, meal.quantity)  # Limit to 5 or available quantity, whichever is smaller
    
    for i in range(1, max_portions + 1):
        portion_buttons.append(
            types.InlineKeyboardButton(
                text=str(i),
                callback_data=f"select_portions:{meal.id}:{i}"
            )
        )
    
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[portion_buttons]
    )
    
    # Send detailed meal information
    await callback_query.message.answer(
        TEXT["meal_details_header"] + 
        TEXT["meal_details"].format(
            name=meal.name,
            description=meal.description,
            price=meal.price,
            vendor=meal.vendor.name,
            quantity=meal.quantity,
            pickup_start=pickup_start,
            pickup_end=pickup_end,
            address=meal.location_address
        ) + 
        "\n\n" + TEXT["select_portions"],
        reply_markup=keyboard
    )
    
    # Answer the callback query
    await callback_query.answer()


@dp.callback_query(lambda c: c.data and c.data.startswith('select_portions:'))
async def callback_select_portions(callback_query: CallbackQuery):
    """Handler for portion selection callback"""
    # Parse callback data
    parts = callback_query.data.split(':')
    meal_id = int(parts[1])
    count = int(parts[2])
    
    # Track portion selection metric
    await track_metric(
        metric_type=MetricType.PORTION_SELECTION,
        entity_id=meal_id,
        user_id=callback_query.from_user.id,
        value=float(count),
        metadata={"portions_selected": count}
    )
    
    # Get the meal
    meal = await Meal.filter(id=meal_id, is_active=True).first()
    
    if not meal or meal.quantity < count:
        await callback_query.answer(TEXT["meal_not_found"])
        return
    
    # Calculate total price
    total_price = meal.price * count
    
    # Create Buy button
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(
                text=TEXT["meal_view_button"],
                callback_data=f"buy_meal:{meal.id}:{count}"
            )]
        ]
    )
    
    # Display the selection and total price
    await callback_query.message.answer(
        TEXT["portion_selection"].format(
            count=count,
            name=meal.name,
            total_price=total_price
        ),
        reply_markup=keyboard
    )
    
    # Answer the callback query
    await callback_query.answer()


@dp.callback_query(lambda c: c.data and c.data.startswith('buy_meal:'))
async def process_buy_callback(callback_query: CallbackQuery):
    """Handler for Buy button callback"""
    # Parse callback data
    parts = callback_query.data.split(':')
    meal_id = int(parts[1])
    count = int(parts[2])
    
    user_id = callback_query.from_user.id
    
    # Get the meal
    meal = await Meal.filter(id=meal_id, is_active=True).prefetch_related('vendor').first()
    
    if not meal or meal.quantity < count:
        await callback_query.answer("Это блюдо больше не доступно или количество порций уменьшилось.")
        return
    
    # Get the consumer
    consumer = await Consumer.filter(telegram_id=user_id).first()
    
    # Create order
    order = await Order.create(
        consumer=consumer,
        meal=meal,
        status=OrderStatus.PENDING,
        quantity=count
    )
    
    # Track order creation metric
    await track_metric(
        metric_type=MetricType.ORDER_CREATED,
        entity_id=order.id,
        user_id=user_id,
        value=float(count),
        metadata={
            "meal_id": meal.id,
            "meal_name": meal.name,
            "vendor_id": meal.vendor.id,
            "vendor_name": meal.vendor.name,
            "order_quantity": count,
            "order_value": float(meal.price * count)
        }
    )
    
    # Calculate total price
    total_price = meal.price * count
    
    # Check if Telegram payments are available
    if payment_gateway.is_telegram_payments_available():
        # Use Telegram's built-in payment system
        payment_id, _ = await payment_gateway.create_payment(order.id, total_price)
        
        # Update order with payment ID
        order.payment_id = payment_id
        await order.save()
        
        # Create Telegram invoice
        prices = [
            types.LabeledPrice(
                label=f"{meal.name} x {count}",
                amount=int(total_price * 100)  # Amount in smallest currency units (cents/kopecks)
            )
        ]
        
        # Send invoice
        try:
            await bot.send_invoice(
                chat_id=user_id,
                title=TEXT["payment_title"],
                description=TEXT["payment_description"].format(
                    meal_name=meal.name,
                    count=count
                ),
                payload=TEXT["payment_payload"].format(order_id=order.id),
                provider_token=payment_gateway.telegram_provider_token,
                currency=payment_gateway.currency,
                prices=prices,
                start_parameter=f"order_{order.id}",
                need_name=False,
                need_phone_number=False,
                need_email=False,
                need_shipping_address=False,
                is_flexible=False,
                protect_content=True
            )
            
            # Send information message
            await callback_query.message.answer(
                TEXT["order_created"].format(
                    order_id=order.id,
                    meal_name=meal.name,
                    quantity=count,
                    price=total_price
                )
            )
            
            # Answer the callback query
            await callback_query.answer()
            
        except Exception as e:
            logging.error(f"Error sending invoice: {e}")
            await callback_query.answer(TEXT["payment_not_available"])
    else:
        # Fall back to legacy payment method (external payment gateway)
        payment_id, payment_url = await payment_gateway.create_payment(order.id, total_price)
        
        if not payment_id or not payment_url:
            await callback_query.answer("Не удалось создать платеж. Пожалуйста, попробуйте позже.")
            return
        
        # Update order with payment ID
        order.payment_id = payment_id
        await order.save()
        
        # Create payment button
        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(
                    text=TEXT["order_payment_button"],
                    url=payment_url
                )]
            ]
        )
        
        # Send order confirmation message
        await callback_query.message.answer(
            TEXT["order_created"].format(
                order_id=order.id,
                meal_name=meal.name,
                quantity=order.quantity,
                price=total_price
            ),
            reply_markup=keyboard
        )
        
        # Answer the callback query
        await callback_query.answer()
        
        # For demo/testing purposes, simulate a payment webhook after 10 seconds
        # This would be replaced by an actual payment provider webhook in production
        asyncio.create_task(simulate_payment_webhook(order.id, payment_id))


@dp.message(Command("meals_nearby"))
@rate_limit(limit=RATE_LIMIT_GENERAL, period=60, key="meals_nearby_command")
async def cmd_meals_nearby(message: Message, state: FSMContext):
    """Handler for /meals_nearby command - Shows nearby meals"""
    user_id = message.from_user.id
    
    # Register user if not already registered
    consumer, created = await Consumer.get_or_create(telegram_id=user_id)
    
    # Create keyboard with location button
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Отправить геопозицию", request_location=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    
    # Start nearby meals search
    await state.set_state(MealsNearbySearch.waiting_for_location)
    await message.answer(TEXT["meals_nearby_prompt"], reply_markup=keyboard)


def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points using Haversine formula"""
    # Earth radius in kilometers
    earth_radius = 6371.0
    
    # Convert latitude and longitude from degrees to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Differences in coordinates
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    # Haversine formula
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = earth_radius * c
    
    return distance


async def filter_meals_by_distance(meals, lat, lon, max_distance=10.0):
    """Filter meals by distance and sort them by proximity"""
    meals_with_distance = []
    
    for meal in meals:
        # Skip meals without coordinates
        if not meal.location_latitude or not meal.location_longitude:
            continue
        
        # Calculate distance
        distance = calculate_distance(lat, lon, meal.location_latitude, meal.location_longitude)
        
        # Add to list if within max_distance
        if distance <= max_distance:
            meals_with_distance.append((meal, distance))
    
    # Sort by distance
    meals_with_distance.sort(key=lambda x: x[1])
    
    # Return meals with their distances
    return meals_with_distance


@dp.message(MealsNearbySearch.waiting_for_location)
async def process_meals_nearby(message: Message, state: FSMContext):
    """Handler to process nearby meals search based on user location"""
    # Check if we received a location
    if not message.location:
        await message.answer(TEXT["meals_nearby_prompt"])
        return
    
    # Clear the state
    await state.clear()
    
    # Get the latitude and longitude
    user_lat = message.location.latitude
    user_lon = message.location.longitude
    
    # Track nearby search metric
    await track_metric(
        metric_type=MetricType.NEARBY_SEARCH,
        user_id=message.from_user.id,
        metadata={
            "latitude": user_lat,
            "longitude": user_lon
        }
    )
    
    # Get all active meals with quantity > 0
    current_time = get_current_almaty_time()
    logging.info(f"Current Almaty time for nearby meal filtering: {current_time}")
    
    # Get all meals first, then filter in memory to ensure proper timezone handling
    all_meals = await Meal.filter(
        is_active=True,
        quantity__gt=0
    ).prefetch_related('vendor')
    
    # Filter meals in memory based on pickup time
    valid_meals = []
    for meal in all_meals:
        # Ensure end time is timezone-aware and in Almaty timezone
        pickup_end_time = ensure_timezone_aware(meal.pickup_end_time)
        if pickup_end_time > current_time:
            valid_meals.append(meal)
    
    if not valid_meals:
        await message.answer(TEXT["browse_meals_empty"], reply_markup=get_main_keyboard())
        return
    
    # Define maximum distance in kilometers
    max_distance = 10.0
    
    # Filter and sort meals by distance
    nearby_meals = await filter_meals_by_distance(valid_meals, user_lat, user_lon, max_distance)
    
    if not nearby_meals:
        await message.answer(
            TEXT["meals_nearby_empty"].format(radius=max_distance),
            reply_markup=get_main_keyboard()
        )
        return
    
    # Send a response for each nearby meal
    for meal, distance in nearby_meals:
        # Create inline keyboard with View button
        keyboard = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [types.InlineKeyboardButton(
                    text=TEXT["view_meal_button"], 
                    callback_data=f"view_meal:{meal.id}"
                )]
            ]
        )
        
        # Format pickup times
        pickup_start = format_pickup_time(meal.pickup_start_time)
        pickup_end = format_pickup_time(meal.pickup_end_time)
        
        # Send message with meal details and View button
        await message.answer(
            TEXT["meals_nearby_item"].format(
                id=meal.id,
                name=meal.name,
                price=meal.price,
                distance=distance,
                vendor=meal.vendor.name,
                quantity=meal.quantity,
                pickup_start=pickup_start,
                pickup_end=pickup_end
            ),
            reply_markup=keyboard
        )


@dp.message(Command("view_meal"))
@rate_limit(limit=RATE_LIMIT_GENERAL, period=60, key="view_meal_command")
async def cmd_view_meal(message: Message):
    """Handler for /view_meal command - Shows detailed meal information"""
    user_id = message.from_user.id
    
    # Register user if not already registered
    consumer, created = await Consumer.get_or_create(telegram_id=user_id)
    
    # Get meal ID from command arguments
    command_parts = message.text.split()
    if len(command_parts) != 2:
        await message.answer("Используйте формат: /view_meal ID", reply_markup=get_main_keyboard())
        return
    
    try:
        meal_id = int(command_parts[1])
        
        # Simulate the view_meal callback to reuse the same logic
        await callback_view_meal(types.CallbackQuery(
            id="manual_command",
            from_user=message.from_user,
            chat_instance=str(message.chat.id),
            message=message,
            data=f"view_meal:{meal_id}"
        ))
    
    except (ValueError, TypeError):
        await message.answer(TEXT["meal_id_invalid"], reply_markup=get_main_keyboard())


@dp.message(lambda message: message.text == "📍 Блюда поблизости")
@rate_limit(limit=RATE_LIMIT_GENERAL, period=60, key="meals_nearby_button")
async def button_meals_nearby(message: Message, state: FSMContext):
    """Handler for meals nearby button"""
    await cmd_meals_nearby(message, state)


@dp.message(lambda message: message.text == "🏪 Зарегистрироваться как поставщик")
@rate_limit(limit=RATE_LIMIT_REGISTER, period=60, key="register_vendor_button")
async def button_register_vendor(message: Message, state: FSMContext):
    """Handler for register vendor button"""
    await cmd_register_vendor(message, state)


@dp.message(lambda message: message.text == "❓ Помощь")
@rate_limit(limit=RATE_LIMIT_GENERAL, period=60, key="help_button")
async def button_help(message: Message):
    """Handler for help button"""
    await cmd_help(message)


# Payment simulation for testing 
async def simulate_payment_webhook(order_id, payment_id):
    """
    Simulates a payment webhook notification.
    In a real application, this would be triggered by a payment provider's callback.
    """
    try:
        # Wait for 10 seconds to simulate payment processing
        await asyncio.sleep(10)
        
        # Create a simulated webhook payload
        webhook_data = {
            "payment_id": payment_id,
            "status": "completed",
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        # Call the payment webhook handler
        await process_payment_webhook(webhook_data)
        
    except Exception as e:
        logging.error(f"Error in payment simulation: {e}")


async def send_order_notifications(order_id):
    """Send notifications to both consumer and vendor about a successful order."""
    try:
        # Get the order with related models
        order = await Order.filter(id=order_id).prefetch_related('consumer', 'meal', 'meal__vendor').first()
        
        if not order:
            logging.error(f"Order not found for notifications: {order_id}")
            return
        
        # Get related models
        meal = order.meal
        vendor = meal.vendor
        
        if not vendor:
            logging.error(f"Vendor not found for order: {order_id}")
            return
        
        # Format pickup times
        pickup_start = format_pickup_time(meal.pickup_start_time)
        pickup_end = format_pickup_time(meal.pickup_end_time)
        
        # Notify the consumer
        consumer_message = TEXT["order_confirmed"].format(
            order_id=order.id,
            meal_name=meal.name,
            quantity=order.quantity,
            vendor_name=vendor.name,
            address=meal.location_address,
            pickup_start=pickup_start,
            pickup_end=pickup_end
        )
        
        await bot.send_message(
            chat_id=order.consumer.telegram_id,
            text=consumer_message,
            reply_markup=get_main_keyboard()
        )
        
        # Notify the vendor
        vendor_message = TEXT["vendor_notification"].format(
            order_id=order.id,
            meal_name=meal.name,
            quantity=order.quantity,
            pickup_start=pickup_start,
            pickup_end=pickup_end
        )
        
        await bot.send_message(
            chat_id=vendor.telegram_id,
            text=vendor_message
        )
        
    except Exception as e:
        logging.error(f"Error sending order notifications: {e}")


async def process_payment_webhook(webhook_data, signature=None):
    """
    Process payment webhook notification from payment provider.
    In production, this would be triggered by a real payment provider webhook.
    """
    try:
        # Verify webhook (in production, this would include verifying the signature)
        payment_id = webhook_data.get("payment_id")
        status = webhook_data.get("status")
        
        if not payment_id or status != "completed":
            logging.error(f"Invalid webhook data: {webhook_data}")
            return False
        
        # Find the order with this payment ID
        order = await Order.filter(payment_id=payment_id).prefetch_related('meal', 'consumer').first()
        
        if not order:
            logging.error(f"Order not found for payment ID: {payment_id}")
            return False
        
        # Check if the order is already paid (to prevent duplicate processing)
        if order.status != OrderStatus.PENDING:
            logging.info(f"Order {order.id} already processed, status: {order.status}")
            return True
        
        # Update the order status
        order.status = OrderStatus.PAID
        await order.save()
        
        # Track payment metric
        await track_metric(
            metric_type=MetricType.ORDER_PAID,
            entity_id=order.id,
            user_id=order.consumer.telegram_id,
            value=float(order.quantity),
            metadata={
                "meal_id": order.meal.id,
                "meal_name": order.meal.name,
                "order_quantity": order.quantity,
                "order_value": float(order.meal.price * order.quantity)
            }
        )
        
        # Update the meal quantity
        meal = order.meal
        meal.quantity = max(0, meal.quantity - order.quantity)
        await meal.save()
        
        # Send notifications
        await send_order_notifications(order.id)
        
        return True
        
    except Exception as e:
        logging.error(f"Error processing payment webhook: {e}")
        return False


@dp.message(Command("my_orders"))
@rate_limit(limit=RATE_LIMIT_GENERAL, period=60, key="my_orders_command")
async def cmd_my_orders(message: Message):
    """Handler for /my_orders command - Shows user's order history"""
    user_id = message.from_user.id
    
    # Check if the user is a registered consumer
    consumer = await Consumer.filter(telegram_id=user_id).first()
    if not consumer:
        await message.answer("У вас пока нет заказов. Начните с просмотра доступных блюд.", reply_markup=get_main_keyboard())
        return
        
    # Get all orders for the consumer
    orders = await Order.filter(consumer=consumer).prefetch_related('meal', 'meal__vendor').order_by('-created_at')
    
    if not orders:
        await message.answer("У вас пока нет заказов. Начните с просмотра доступных блюд.", reply_markup=get_main_keyboard())
        return
        
    # Display orders
    response = "Ваши заказы:\n\n"
    
    for order in orders:
        meal = await order.meal
        status_text = {
            OrderStatus.PENDING: "В обработке",
            OrderStatus.PAID: "Оплачен",
            OrderStatus.COMPLETED: "Выполнен",
            OrderStatus.CANCELLED: "Отменен"
        }.get(order.status, "Неизвестно")
        
        response += (
            f"Заказ #{order.id}\n"
            f"Блюдо: {meal.name}\n"
            f"Количество: {order.quantity} порций\n"
            f"Статус: {status_text}\n"
            f"Дата: {order.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
        )
    
    await message.answer(response, reply_markup=get_main_keyboard())


@dp.message(Command("vendor_orders"))
@rate_limit(limit=RATE_LIMIT_GENERAL, period=60, key="vendor_orders_command")
async def cmd_vendor_orders(message: Message):
    """Handler for /vendor_orders command - Shows vendor's order history"""
    user_id = message.from_user.id
    
    # Check if the user is a registered and approved vendor
    vendor = await Vendor.filter(telegram_id=user_id, status=VendorStatus.APPROVED).first()
    if not vendor:
        await message.answer("Эта команда доступна только для одобренных поставщиков.", reply_markup=get_main_keyboard())
        return
        
    # Get all the vendor's meals
    vendor_meals = await Meal.filter(vendor=vendor).values_list('id', flat=True)
    
    if not vendor_meals:
        await message.answer("У вас пока нет активных блюд и заказов.", reply_markup=get_main_keyboard())
        return
    
    # Get orders for the vendor's meals
    orders = await Order.filter(meal_id__in=vendor_meals).prefetch_related('meal', 'consumer').order_by('-created_at')
    
    if not orders:
        await message.answer("У вас пока нет заказов на ваши блюда.", reply_markup=get_main_keyboard())
        return
        
    # Display orders
    response = "Заказы на ваши блюда:\n\n"
    
    for order in orders:
        meal = await order.meal
        status_text = {
            OrderStatus.PENDING: "В обработке",
            OrderStatus.PAID: "Оплачен",
            OrderStatus.COMPLETED: "Выполнен",
            OrderStatus.CANCELLED: "Отменен"
        }.get(order.status, "Неизвестно")
        
        response += (
            f"Заказ #{order.id}\n"
            f"Блюдо: {meal.name}\n"
            f"Количество: {order.quantity} порций\n"
            f"Статус: {status_text}\n"
            f"Дата: {order.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
        )
    
    await message.answer(response, reply_markup=get_main_keyboard())

# ---------------------------------------------------------------------------
# /complete_order – поставщик подтверждает, что покупатель забрал заказ
# ---------------------------------------------------------------------------
@dp.message(Command("complete_order"))
@rate_limit(limit=RATE_LIMIT_GENERAL, period=60, key="complete_order_command")
async def cmd_complete_order(message: Message):
    """Handler for vendor to complete an order"""
    user_id = message.from_user.id
    
    # Check if sender is a vendor
    vendor = await Vendor.filter(telegram_id=user_id).first()
    if not vendor:
        await message.answer(TEXT["not_vendor"], reply_markup=get_main_keyboard())
        return
    
    # Check if vendor is approved
    if vendor.status != VendorStatus.APPROVED:
        await message.answer(TEXT["vendor_not_approved"], reply_markup=get_main_keyboard())
        return
    
    # Parse order ID from command
    args = message.text.split()
    if len(args) < 2:
        await message.answer(TEXT["order_complete_usage"], reply_markup=get_main_keyboard())
        return
    
    try:
        order_id = int(args[1])
        
        # Get the order and check if it belongs to this vendor's meal
        order = await Order.filter(id=order_id).prefetch_related('meal', 'meal__vendor', 'consumer').first()
        
        if not order:
            await message.answer(TEXT["order_not_found"].format(order_id=order_id), reply_markup=get_main_keyboard())
            return
        
        # Verify the meal belongs to this vendor
        if order.meal.vendor.id != vendor.id:
            await message.answer(TEXT["meal_not_found"], reply_markup=get_main_keyboard())
            return
        
        # Check order status is PAID
        if order.status != OrderStatus.PAID:
            await message.answer(TEXT["order_complete_not_paid"], reply_markup=get_main_keyboard())
            return
        
        # Update order status to COMPLETED
        order.status = OrderStatus.COMPLETED
        order.completed_at = get_current_almaty_time()
        await order.save()
        
        # Track order completion metric
        await track_metric(
            metric_type=MetricType.ORDER_COMPLETED,
            entity_id=order.id,
            user_id=user_id,
            value=float(order.quantity),
            metadata={
                "meal_id": order.meal.id,
                "meal_name": order.meal.name,
                "consumer_id": order.consumer.telegram_id,
                "order_quantity": order.quantity,
                "order_value": float(order.meal.price * order.quantity)
            }
        )
        
        # Notify the vendor
        await message.answer(TEXT["order_mark_completed"].format(order_id=order.id), reply_markup=get_main_keyboard())
        
        # Notify the consumer
        consumer_message = (
            f"✅ Ваш заказ #{order.id} был отмечен как выполненный!\n\n"
            f"Блюдо: {order.meal.name}\n"
            f"Количество порций: {order.quantity}\n"
            f"Поставщик: {vendor.name}\n\n"
            f"Спасибо за использование сервиса As Bolsyn!"
        )
        
        await bot.send_message(
            chat_id=order.consumer.telegram_id,
            text=consumer_message
        )
        
    except ValueError:
        await message.answer("Неверный формат ID заказа. Используйте число.", reply_markup=get_main_keyboard())
    except Exception as e:
        logging.error(f"Error completing order: {e}")
        await message.answer(f"Произошла ошибка при выполнении заказа: {e}", reply_markup=get_main_keyboard())

# ---------------------------------------------------------------------------
# /cancel_order – admin отменяет заказ, который застрял в статусе pending
# ---------------------------------------------------------------------------
@dp.message(Command("cancel_order"))
@rate_limit(limit=RATE_LIMIT_GENERAL, period=60, key="cancel_order_command")
async def cmd_cancel_order(message: Message):
    """Handler for admin to cancel a stuck order"""
    user_id = message.from_user.id
    
    # Check if sender is admin
    if str(user_id) != ADMIN_CHAT_ID:
        await message.answer(TEXT["not_admin"], reply_markup=get_main_keyboard())
        return
    
    # Parse order ID from command
    args = message.text.split()
    if len(args) < 2:
        await message.answer(TEXT["order_cancel_usage"], reply_markup=get_main_keyboard())
        return
    
    try:
        order_id = int(args[1])
        
        # Get the order
        order = await Order.filter(id=order_id).prefetch_related('meal', 'meal__vendor', 'consumer').first()
        
        if not order:
            await message.answer(TEXT["order_not_found"].format(order_id=order_id), reply_markup=get_main_keyboard())
            return
        
        # Update order status to CANCELLED
        previous_status = order.status
        order.status = OrderStatus.CANCELLED
        await order.save()
        
        # Track order cancellation metric
        await track_metric(
            metric_type=MetricType.ORDER_CANCELLED,
            entity_id=order.id,
            user_id=user_id,
            metadata={
                "meal_id": order.meal.id,
                "meal_name": order.meal.name,
                "previous_status": previous_status,
                "order_quantity": order.quantity
            }
        )
        
        # Notify the admin
        await message.answer(TEXT["order_cancel_success"].format(order_id=order.id), reply_markup=get_main_keyboard())
        
        # Notify the consumer if possible
        try:
            consumer_message = (
                f"❌ Ваш заказ #{order.id} был отменен администратором.\n\n"
                f"Блюдо: {order.meal.name}\n"
                f"Количество порций: {order.quantity}\n\n"
                f"Пожалуйста, свяжитесь с поддержкой, если у вас есть вопросы."
            )
            
            await bot.send_message(
                chat_id=order.consumer.telegram_id,
                text=consumer_message
            )
        except Exception as e:
            logging.error(f"Error notifying consumer about order cancellation: {e}")
        
        # Notify the vendor if possible
        try:
            vendor = await order.meal.vendor
            vendor_message = (
                f"❌ Заказ #{order.id} был отменен администратором.\n\n"
                f"Блюдо: {order.meal.name}\n"
                f"Количество порций: {order.quantity}\n\n"
                f"Пожалуйста, свяжитесь с поддержкой, если у вас есть вопросы."
            )
            
            await bot.send_message(
                chat_id=vendor.telegram_id,
                text=vendor_message
            )
        except Exception as e:
            logging.error(f"Error notifying vendor about order cancellation: {e}")
        
    except ValueError:
        await message.answer("Неверный формат ID заказа. Используйте число.", reply_markup=get_main_keyboard())
    except Exception as e:
        logging.error(f"Error cancelling order: {e}")
        await message.answer(f"Произошла ошибка при отмене заказа: {e}", reply_markup=get_main_keyboard())

# Add a new command for viewing metrics (admin only)
@dp.message(Command("metrics"))
@rate_limit(limit=RATE_LIMIT_GENERAL, period=60, key="metrics_command")
async def cmd_metrics(message: Message):
    """Handler for admin to view metrics dashboard"""
    user_id = message.from_user.id
    
    # Only admin can view metrics
    if str(user_id) != ADMIN_CHAT_ID:
        await message.answer(TEXT["not_admin"], reply_markup=get_main_keyboard())
        return
    
    try:
        # Get metrics dashboard data
        dashboard = await get_metrics_dashboard_data()
        
        # Format the dashboard data as a readable message
        overview = dashboard.get("overview", {})
        
        metrics_text = (
            "📊 *Метрики As Bolsyn*\n\n"
            "*Общая статистика:*\n"
            f"• Пользователей: {overview.get('total_users', 0)}\n"
            f"• Поставщиков: {overview.get('approved_vendors', 0)}/{overview.get('total_vendors', 0)}\n"
            f"• Активных блюд: {overview.get('active_meals', 0)}\n"
            f"• Всего блюд: {overview.get('total_meals_ever', 0)}\n"
            f"• Оплаченных заказов: {overview.get('paid_orders', 0)}\n"
            f"• Завершенных заказов: {overview.get('completed_orders', 0)}\n"
            f"• Общий оборот: {overview.get('gmv_total', 0)} тг\n\n"
        )
        
        # Add conversion rates from the last 7 days
        conversion = dashboard.get("weekly", {}).get("conversion_rates", {})
        if isinstance(conversion, dict):
            metrics_text += (
                "*Конверсии (7 дней):*\n"
                f"• Просмотр → Детали: {conversion.get('browse_to_view', 0)}%\n"
                f"• Детали → Заказ: {conversion.get('view_to_order', 0)}%\n"
                f"• Заказ → Оплата: {conversion.get('order_to_payment', 0)}%\n"
                f"• Просмотр → Покупка: {conversion.get('overall_browse_to_purchase', 0)}%\n"
            )
        
        # Send the formatted metrics message
        await message.answer(metrics_text, parse_mode="Markdown")
        
        # Generate a detailed report for the last 30 days
        thirty_days_ago = datetime.datetime.now() - datetime.timedelta(days=30)
        detailed_report = await get_metrics_report(start_date=thirty_days_ago)
        
        # Convert the report to a formatted string (simplified for readability)
        report_text = (
            "📝 *Детальный отчет (30 дней)*\n\n"
            f"Период: {detailed_report['time_period']['start_date']} — {detailed_report['time_period']['end_date']}\n\n"
        )
        
        # Add count summary
        counts = detailed_report.get("summary", {}).get("counts", {})
        if counts:
            report_text += "*События:*\n"
            for event_type, count in counts.items():
                # Convert snake_case to readable text
                readable_type = " ".join(event_type.split("_")).capitalize()
                report_text += f"• {readable_type}: {count}\n"
        
        # Send the detailed report
        await message.answer(report_text, parse_mode="Markdown")
        
    except Exception as e:
        logging.error(f"Error generating metrics: {e}")
        await message.answer(f"Произошла ошибка при получении метрик: {e}", reply_markup=get_main_keyboard())


@dp.message(lambda message: message.text == "📋 Просмотреть блюда")
@rate_limit(limit=RATE_LIMIT_GENERAL, period=60, key="browse_meals_button")
async def button_browse_meals(message: Message):
    """Handler for browse meals button"""
    await cmd_browse_meals(message)


@dp.message(lambda message: message.text == "🛒 Мои заказы")
@rate_limit(limit=RATE_LIMIT_GENERAL, period=60, key="my_orders_button")
async def button_my_orders(message: Message):
    """Handler for my orders button"""
    await cmd_my_orders(message)


async def main():
    """Main function to run the bot in simple polling mode"""
    # Initialize database connection
    await init_db()
    
    try:
        # Create background task for deactivating expired meals
        asyncio.create_task(periodic_task_runner())
        
        # Start the bot
        await dp.start_polling(bot)
    finally:
        # Close database connection when done
        await close_db()

async def periodic_task_runner():
    """Run scheduled tasks periodically"""
    while True:
        try:
            # Run task to deactivate expired meals
            await scheduled_tasks["deactivate_expired_meals"]()
            # Wait for 10 minutes before checking again
            await asyncio.sleep(600)
        except Exception as e:
            logging.error(f"Error in periodic task runner: {e}")
            # Wait a bit before retry in case of error
            await asyncio.sleep(60)

# Payment related handlers
@dp.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: types.PreCheckoutQuery):
    """
    Handler for pre-checkout queries from Telegram payments
    This is called when a user initiates a payment through Telegram
    """
    try:
        # Extract order ID from payload
        # Expected format: "order_123" where 123 is the order ID
        payload = pre_checkout_query.invoice_payload
        order_id = int(payload.split('_')[1])
        
        # Verify the order exists and is still pending
        order = await Order.filter(id=order_id, status=OrderStatus.PENDING).prefetch_related('meal').first()
        
        # If order not found or not in PENDING status, reject the checkout
        if not order:
            await bot.answer_pre_checkout_query(
                pre_checkout_query_id=pre_checkout_query.id,
                ok=False,
                error_message=TEXT["order_not_found"].format(order_id=order_id)
            )
            return
            
        # Verify meal is still available and has enough quantity
        meal = order.meal
        if not meal.is_active or meal.quantity < order.quantity:
            await bot.answer_pre_checkout_query(
                pre_checkout_query_id=pre_checkout_query.id,
                ok=False,
                error_message="Блюдо больше не доступно или количество порций уменьшилось."
            )
            return
            
        # All checks passed, approve the checkout
        await bot.answer_pre_checkout_query(
            pre_checkout_query_id=pre_checkout_query.id,
            ok=True
        )
        
    except Exception as e:
        logging.error(f"Error processing pre-checkout query: {e}")
        # If any error occurred, reject the checkout
        await bot.answer_pre_checkout_query(
            pre_checkout_query_id=pre_checkout_query.id,
            ok=False,
            error_message=TEXT["payment_checkout_failed"]
        )


@dp.message(lambda message: getattr(message, 'content_type', None) == types.ContentType.SUCCESSFUL_PAYMENT)
async def process_successful_payment(message: Message):
    """
    Handler for successful payments through Telegram
    This is called when a user successfully completes payment
    """
    success = False  # Flag to track if the entire process completed successfully
    
    try:
        # Get payment info
        payment = message.successful_payment
        
        # Extract order ID from payload
        payload = payment.invoice_payload
        order_id = int(payload.split('_')[1])
        
        # Get the order with all related models
        order = await Order.filter(id=order_id).prefetch_related('meal', 'consumer', 'meal__vendor').first()
        
        if not order:
            logging.error(f"Order {order_id} not found for successful payment")
            await message.answer(TEXT["order_not_found"].format(order_id=order_id))
            return
        
        # Update order status to PAID
        order.status = OrderStatus.PAID
        await order.save()
        
        # Validate meal and vendor information
        meal = order.meal
        if not meal:
            logging.error(f"Meal not found for order {order_id}")
            await message.answer("К сожалению, информация о блюде не найдена, но ваш платеж был успешно обработан. Пожалуйста, свяжитесь с поддержкой для уточнения деталей заказа.")
            return
            
        vendor = meal.vendor
        if not vendor:
            logging.error(f"Vendor not found for meal {meal.id} in order {order_id}")
            await message.answer("К сожалению, информация о поставщике не найдена, но ваш платеж был успешно обработан. Пожалуйста, свяжитесь с поддержкой для уточнения деталей заказа.")
            return
        
        # Update meal quantity
        meal.quantity = max(0, meal.quantity - order.quantity)
        await meal.save()
        
        # Track payment metric
        await track_metric(
            metric_type=MetricType.ORDER_PAID,
            entity_id=order.id,
            user_id=order.consumer.telegram_id,
            value=float(order.quantity),
            metadata={
                "meal_id": meal.id,
                "meal_name": meal.name,
                "order_quantity": order.quantity,
                "order_value": float(meal.price * order.quantity),
                "payment_method": "telegram"
            }
        )
        
        # Format pickup times for message
        pickup_start = format_pickup_time(meal.pickup_start_time)
        pickup_end = format_pickup_time(meal.pickup_end_time)
        
        # Send order confirmation to consumer
        await message.answer(
            TEXT["order_confirmed"].format(
                order_id=order.id,
                meal_name=meal.name,
                quantity=order.quantity,
                vendor_name=vendor.name,
                address=meal.location_address,
                pickup_start=pickup_start,
                pickup_end=pickup_end
            )
        )
        
        # Send notification to vendor about new order 
        try:
            # Send vendor notification
            vendor_message = TEXT["vendor_notification"].format(
                order_id=order.id,
                meal_name=meal.name,
                quantity=order.quantity,
                pickup_start=pickup_start,
                pickup_end=pickup_end
            )
            
            await bot.send_message(
                chat_id=vendor.telegram_id,
                text=vendor_message
            )
        except Exception as vendor_notification_error:
            logging.error(f"Error notifying vendor: {vendor_notification_error}")
            # Don't send an error message to the user since this is not critical
            
        # All steps completed successfully
        success = True
        
        # Show payment successful message
        await message.answer(TEXT["payment_successful"].format(order_id=order.id))
        
    except Exception as e:
        logging.error(f"Error processing successful payment: {e}")
        
        # Only show error message if we haven't already shown success
        if not success:
            # Check if we at least managed to update the order status
            try:
                if 'order' in locals() and order and order.status == OrderStatus.PAID:
                    await message.answer(f"Ваш платеж был успешно обработан и заказ #{order.id} отмечен как оплаченный, но возникла ошибка при обработке дополнительной информации. Пожалуйста, проверьте статус вашего заказа в разделе 'Мои заказы'.")
                else:
                    await message.answer("Произошла ошибка при обработке платежа. Обратитесь в поддержку.")
            except Exception:
                await message.answer("Произошла ошибка при обработке платежа. Обратитесь в поддержку.")


if __name__ == "__main__":
    """Entry point for running the bot in polling mode directly"""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot stopped!")