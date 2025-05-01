import asyncio
import logging
import datetime
import math
from decimal import Decimal
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from .config import BOT_TOKEN, ADMIN_CHAT_ID
from .db import init_db, close_db
from .models import Consumer, Vendor, VendorStatus, Meal, Order, OrderStatus

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher with FSM storage
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Russian text templates
TEXT = {
    "welcome": "Добро пожаловать в As Bolsyn! Этот бот поможет вам найти и приобрести блюда от местных заведений по сниженным ценам.",
    "help": "Доступные команды:\n/start - Запустить бот\n/help - Показать эту справку\n/register_vendor - Зарегистрироваться как поставщик\n/add_meal - Добавить блюдо (только для поставщиков)\n/my_meals - Просмотреть мои блюда (только для поставщиков)\n/browse_meals - Просмотреть доступные блюда\n/meals_nearby - Найти блюда поблизости\n/view_meal <id> - Посмотреть детали блюда\n/my_orders - Просмотреть мои заказы\n/vendor_orders - Просмотреть заказы на мои блюда (только для поставщиков)",
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
    "order_created": "Заказ #{order_id} создан. Пожалуйста, перейдите по ссылке для оплаты.",
    "payment_pending": "После успешной оплаты вы получите подтверждение. Если вы не получили подтверждение в течение 5 минут, пожалуйста, свяжитесь с поддержкой.",
    "order_confirmed": "✅ Заказ #{order_id} успешно оплачен!\n\nДетали заказа:\n- Блюдо: {meal_name}\n- Количество порций: {quantity}\n- Поставщик: {vendor_name}\n- Адрес самовывоза: {address}\n- Время самовывоза: с {pickup_start} до {pickup_end}\n\nПожалуйста, сохраните номер заказа #{order_id} для предъявления поставщику при получении.",
    "vendor_notification": "🔔 Новый оплаченный заказ #{order_id}!\n\nДетали заказа:\n- Блюдо: {meal_name}\n- Количество порций: {quantity}\n- Время самовывоза: с {pickup_start} до {pickup_end}\n\nПожалуйста, подготовьте заказ к указанному времени самовывоза.",
    "payment_failed": "❌ Оплата заказа #{order_id} не удалась. Пожалуйста, попробуйте еще раз или выберите другое блюдо.",
    "my_orders_empty": "У вас пока нет заказов. Начните с просмотра доступных блюд.",
    "vendor_orders_empty": "У вас пока нет заказов на ваши блюда.",
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
async def cmd_start(message: Message):
    """Handler for /start command"""
    # Register user if not already registered
    user_id = message.from_user.id
    consumer, created = await Consumer.get_or_create(telegram_id=user_id)
    
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
async def cmd_help(message: Message):
    """Handler for /help command"""
    await message.answer(TEXT["help"], reply_markup=get_main_keyboard())


@dp.message(Command("register_vendor"))
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
    user_id = message.from_user.id
    
    # Check if user is admin
    if not ADMIN_CHAT_ID or str(user_id) != ADMIN_CHAT_ID:
        await message.answer(TEXT["not_admin"])
        return
    
    # Get vendor ID from command arguments
    command_parts = message.text.split()
    if len(command_parts) != 2:
        await message.answer("Используйте формат: /approve_vendor ID")
        return
    
    try:
        vendor_telegram_id = int(command_parts[1])
        vendor = await Vendor.filter(telegram_id=vendor_telegram_id).first()
        
        if not vendor:
            await message.answer(TEXT["vendor_not_found"].format(telegram_id=vendor_telegram_id))
            return
        
        # Update vendor status
        vendor.status = VendorStatus.APPROVED
        await vendor.save()
        
        # Notify admin about successful approval
        await message.answer(TEXT["admin_approved_vendor"].format(
            telegram_id=vendor_telegram_id,
            name=vendor.name
        ))
        
        # Notify vendor about approval
        await bot.send_message(
            chat_id=vendor_telegram_id,
            text=TEXT["vendor_approved"]
        )
    
    except (ValueError, TypeError):
        await message.answer("Неверный формат ID. Используйте числовой ID.")


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
            
        # Create datetime object for today with the specified time
        now = datetime.datetime.now()
        pickup_start = now.replace(hour=hours, minute=minutes)
        
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
            
        # Create datetime object for today with the specified time
        now = datetime.datetime.now()
        pickup_end = now.replace(hour=hours, minute=minutes)
        
        # Get the pickup start time from state
        data = await state.get_data()
        pickup_start = data.get('pickup_start')
        
        # Ensure end time is after start time
        if pickup_end <= pickup_start:
            # If end time is earlier, assume it's for the next day
            pickup_end = pickup_end.replace(day=pickup_end.day + 1)
        
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
    """Handler to process meal location coordinates and complete creation"""
    user_id = message.from_user.id
    
    # Check if message contains location
    if not message.location:
        await message.answer(TEXT["meal_invalid_location"])
        return
    
    # Save location coordinates
    location = message.location
    await state.update_data(
        location_latitude=location.latitude,
        location_longitude=location.longitude
    )
    
    # Get all data from state
    data = await state.get_data()
    
    # Get vendor
    vendor = await Vendor.filter(telegram_id=user_id).first()
    
    # Create meal in database
    meal = await Meal.create(
        name=data.get('name'),
        description=data.get('description'),
        price=data.get('price'),
        quantity=data.get('quantity'),
        pickup_start_time=data.get('pickup_start'),
        pickup_end_time=data.get('pickup_end'),
        location_address=data.get('location_address'),
        location_latitude=data.get('location_latitude'),
        location_longitude=data.get('location_longitude'),
        vendor=vendor
    )
    
    # Clear the state
    await state.clear()
    
    # Notify the vendor about successful meal creation
    await message.answer(
        TEXT["meal_added_success"].format(
            name=meal.name,
            description=meal.description,
            price=meal.price,
            quantity=meal.quantity,
            pickup_start=data.get('pickup_start_str'),
            pickup_end=data.get('pickup_end_str'),
            address=meal.location_address
        ),
        reply_markup=get_main_keyboard()
    )


@dp.message(Command("my_meals"))
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
        # Format pickup times as strings
        pickup_start = meal.pickup_start_time.strftime("%H:%M")
        pickup_end = meal.pickup_end_time.strftime("%H:%M")
        
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
async def cmd_browse_meals(message: Message):
    """Handler for /browse_meals command - Shows all available meals"""
    user_id = message.from_user.id
    
    # Register user if not already registered
    consumer, created = await Consumer.get_or_create(telegram_id=user_id)
    
    # Get all active meals with quantity > 0, ordered by creation date (newest first)
    meals = await Meal.filter(is_active=True, quantity__gt=0).prefetch_related('vendor').order_by('-created_at')
    
    if not meals:
        await message.answer(TEXT["browse_meals_empty"], reply_markup=get_main_keyboard())
        return
    
    # Process each meal individually with its own inline keyboard
    for meal in meals:
        # Format pickup times
        pickup_start = meal.pickup_start_time.strftime('%H:%M')
        pickup_end = meal.pickup_end_time.strftime('%H:%M')
        
        # Create meal listing text
        meal_text = TEXT["browse_meals_item"].format(
            id=meal.id,
            name=meal.name,
            price=meal.price,
            vendor=meal.vendor.name,
            quantity=meal.quantity,
            pickup_start=pickup_start,
            pickup_end=pickup_end
        )
        
        # Create inline keyboard with View button
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text=TEXT["view_meal_button"], callback_data=f"view_meal:{meal.id}")]
        ])
        
        # Send meal as separate message with its own button
        await message.answer(meal_text, reply_markup=keyboard)
    
    # Return the main keyboard after listing all meals
    await message.answer("Выберите блюдо, нажав на кнопку 'Посмотреть' под интересующим вас блюдом.", reply_markup=get_main_keyboard())


@dp.callback_query(lambda c: c.data and c.data.startswith('view_meal:'))
async def callback_view_meal(callback_query: CallbackQuery):
    """Handler for view meal button callback"""
    # Extract meal ID from callback data
    meal_id = int(callback_query.data.split(':')[1])
    
    # Find the meal
    meal = await Meal.filter(id=meal_id, is_active=True, quantity__gt=0).prefetch_related('vendor').first()
    
    if not meal:
        await callback_query.answer(TEXT["meal_not_found"])
        return
    
    # Format pickup times
    pickup_start = meal.pickup_start_time.strftime('%H:%M')
    pickup_end = meal.pickup_end_time.strftime('%H:%M')
    
    # Create response with detailed meal information
    response = TEXT["meal_details_header"]
    response += TEXT["meal_details"].format(
        name=meal.name,
        description=meal.description,
        price=meal.price,
        vendor=meal.vendor.name,
        quantity=meal.quantity,
        pickup_start=pickup_start,
        pickup_end=pickup_end,
        address=meal.location_address
    )
    
    # Create portion selection buttons
    max_portions = min(5, meal.quantity)  # Limit selection to 5 or available quantity
    buttons = []
    row = []
    
    for i in range(1, max_portions + 1):
        row.append(types.InlineKeyboardButton(text=str(i), callback_data=f"select_portions:{meal.id}:{i}"))
        # Create rows of 5 buttons
        if i % 5 == 0 or i == max_portions:
            buttons.append(row)
            row = []
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=buttons)
    
    # Answer the callback to clear loading state
    await callback_query.answer()
    
    # Send the message with portion selection
    await callback_query.message.answer(response)
    await callback_query.message.answer(TEXT["select_portions"], reply_markup=keyboard)


@dp.callback_query(lambda c: c.data and c.data.startswith('select_portions:'))
async def callback_select_portions(callback_query: CallbackQuery):
    """Handler for portion selection button callback"""
    # Extract meal ID and quantity from callback data
    parts = callback_query.data.split(':')
    meal_id = int(parts[1])
    selected_portions = int(parts[2])
    
    # Find the meal
    meal = await Meal.filter(id=meal_id, is_active=True, quantity__gt=0).prefetch_related('vendor').first()
    
    if not meal:
        await callback_query.answer(TEXT["meal_not_found"])
        return
    
    # Check if enough portions are available
    if selected_portions > meal.quantity:
        await callback_query.answer(f"Доступно только {meal.quantity} порций")
        return
    
    # Calculate total price
    total_price = meal.price * selected_portions
    
    # Create confirmation message
    message = TEXT["portion_selection"].format(
        count=selected_portions,
        name=meal.name,
        total_price=total_price
    )
    
    # Create buy button
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=TEXT["meal_view_button"], callback_data=f"buy_meal:{meal.id}:{selected_portions}")]
    ])
    
    # Answer the callback to clear loading state
    await callback_query.answer()
    
    # Send the confirmation message with buy button
    await callback_query.message.answer(message, reply_markup=keyboard)


@dp.callback_query(lambda c: c.data and c.data.startswith('buy_meal:'))
async def process_buy_callback(callback_query: CallbackQuery):
    """Handler for buy meal button callback - Initiates the payment process"""
    user_id = callback_query.from_user.id
    
    # Extract meal ID and portions from callback data
    parts = callback_query.data.split(':')
    meal_id = int(parts[1])
    portions = int(parts[2]) if len(parts) > 2 else 1
    
    try:
        # Get the meal from the database
        meal = await Meal.filter(id=meal_id, is_active=True).prefetch_related('vendor').first()
        
        if not meal:
            await callback_query.answer("Блюдо не найдено или недоступно.")
            return
            
        if meal.quantity < portions:
            await callback_query.answer(f"Недостаточно порций. Доступно: {meal.quantity}.")
            return
            
        # Get or create consumer
        consumer, created = await Consumer.get_or_create(telegram_id=user_id)
        
        # Calculate total price
        total_price = meal.price * portions
        
        # Create a new order
        order = await Order.create(
            consumer=consumer,
            meal=meal,
            status=OrderStatus.PENDING,
            quantity=portions
        )
        
        # Import the payment gateway here to avoid circular imports
        from .payment import payment_gateway
        
        # Create payment
        payment_id, payment_url = await payment_gateway.create_payment(
            order_id=order.id,
            amount=total_price,
            description=f"Оплата за {portions} порций '{meal.name}'"
        )
        
        if not payment_id or not payment_url:
            await callback_query.answer("Не удалось создать платеж. Пожалуйста, попробуйте позже.")
            return
            
        # Save payment ID to order
        order.payment_id = payment_id
        await order.save()
        
        # Create inline keyboard with payment link
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="Перейти к оплате", url=payment_url)]
        ])
        
        # Notify the user
        await callback_query.message.answer(
            f"Заказ #{order.id} создан. Пожалуйста, перейдите по ссылке для оплаты {portions} порций '{meal.name}' на сумму {total_price} тенге.",
            reply_markup=keyboard
        )
        
        # Add instruction about webhook confirmation
        await callback_query.message.answer(
            "После успешной оплаты вы получите подтверждение. Если вы не получили подтверждение в течение 5 минут, пожалуйста, свяжитесь с поддержкой.",
            reply_markup=get_main_keyboard()
        )
        
        # For the MVP, we'll automatically simulate a successful payment after a delay
        # In a real implementation, this would be handled by the webhook
        asyncio.create_task(simulate_payment_webhook(order.id, payment_id))
        
        await callback_query.answer()
        
    except Exception as e:
        logging.error(f"Error creating order: {e}")
        await callback_query.answer("Произошла ошибка при создании заказа. Пожалуйста, попробуйте позже.")


# Handle text button presses
@dp.message(lambda message: message.text == "📋 Просмотреть блюда")
async def button_browse_meals(message: Message):
    """Handler for browse meals button"""
    await cmd_browse_meals(message)


@dp.message(Command("meals_nearby"))
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
    
    # Return only the meal objects
    return [meal for meal, _ in meals_with_distance]


@dp.message(MealsNearbySearch.waiting_for_location)
async def process_meals_nearby(message: Message, state: FSMContext):
    """Handler to process meals nearby search"""
    user_id = message.from_user.id
    
    # Check if message contains location
    if not message.location:
        await message.answer(TEXT["meal_invalid_location"], reply_markup=get_main_keyboard())
        return
    
    # Clear state
    await state.clear()
    
    # Get location coordinates
    location = message.location
    
    # Define search radius in kilometers
    radius = 10.0
    
    # Get all active meals with quantity > 0
    meals = await Meal.filter(is_active=True, quantity__gt=0).prefetch_related('vendor')
    
    # Filter and sort meals by distance
    nearby_meals = await filter_meals_by_distance(meals, location.latitude, location.longitude, radius)
    
    if not nearby_meals:
        await message.answer(TEXT["meals_nearby_empty"].format(radius=radius), reply_markup=get_main_keyboard())
        return
    
    # Process each meal individually with its own inline keyboard
    for meal in nearby_meals:
        # Calculate distance
        distance = calculate_distance(location.latitude, location.longitude, meal.location_latitude, meal.location_longitude)
        
        # Format pickup times
        pickup_start = meal.pickup_start_time.strftime('%H:%M')
        pickup_end = meal.pickup_end_time.strftime('%H:%M')
        
        # Create meal text
        meal_text = TEXT["meals_nearby_item"].format(
            id=meal.id,
            name=meal.name,
            price=meal.price,
            distance=distance,
            vendor=meal.vendor.name,
            quantity=meal.quantity,
            pickup_start=pickup_start,
            pickup_end=pickup_end
        )
        
        # Create inline keyboard with View button
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text=TEXT["view_meal_button"], callback_data=f"view_meal:{meal.id}")]
        ])
        
        # Send meal as separate message with its own button
        await message.answer(meal_text, reply_markup=keyboard)
    
    # Return the main keyboard after listing all meals
    await message.answer("Выберите блюдо, нажав на кнопку 'Посмотреть' под интересующим вас блюдом.", reply_markup=get_main_keyboard())


@dp.message(Command("view_meal"))
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
async def button_meals_nearby(message: Message, state: FSMContext):
    """Handler for meals nearby button"""
    await cmd_meals_nearby(message, state)


@dp.message(lambda message: message.text == "🏪 Зарегистрироваться как поставщик")
async def button_register_vendor(message: Message, state: FSMContext):
    """Handler for register vendor button"""
    await cmd_register_vendor(message, state)


@dp.message(lambda message: message.text == "❓ Помощь")
async def button_help(message: Message):
    """Handler for help button"""
    await cmd_help(message)


# Payment simulation for testing 
async def simulate_payment_webhook(order_id, payment_id):
    """
    Simulates a payment webhook notification with a successful payment.
    This is only for demo/testing purposes in the MVP.
    In a real implementation, a webhook endpoint would receive notifications from the payment gateway.
    """
    try:
        # Wait a few seconds to simulate the payment process
        await asyncio.sleep(5)
        
        # Simulate webhook payload
        webhook_data = {
            "payment_id": payment_id,
            "order_id": order_id,
            "status": "completed",
            "amount": "0.00",  # Not used in processing
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        # Import the payment gateway to avoid circular imports
        from .payment import payment_gateway
        
        # Process the simulated webhook
        success = await payment_gateway.process_webhook(webhook_data)
        
        if success:
            # Notify the user and vendor about the successful payment
            await send_order_notifications(order_id)
            
    except Exception as e:
        logging.error(f"Error simulating payment webhook: {e}")


async def send_order_notifications(order_id):
    """Send notifications to both consumer and vendor about a successful order."""
    try:
        # Get the order with related models
        order = await Order.filter(id=order_id).prefetch_related('consumer', 'meal', 'meal__vendor').first()
        
        if not order or order.status != OrderStatus.PAID:
            logging.error(f"Order not found or not paid: {order_id}")
            return
            
        # Get details
        consumer = await order.consumer
        meal = await order.meal
        vendor = await meal.vendor
        
        # Generate a unique order identifier for both parties to reference
        order_ref = f"#{order.id}"
        
        # Calculate pickup window
        pickup_start = meal.pickup_start_time.strftime('%H:%M')
        pickup_end = meal.pickup_end_time.strftime('%H:%M')
        
        # Notify the consumer
        consumer_message = (
            f"✅ Заказ {order_ref} успешно оплачен!\n\n"
            f"Детали заказа:\n"
            f"- Блюдо: {meal.name}\n"
            f"- Количество порций: {order.quantity}\n"
            f"- Поставщик: {vendor.name}\n"
            f"- Адрес самовывоза: {meal.location_address}\n"
            f"- Время самовывоза: с {pickup_start} до {pickup_end}\n\n"
            f"Пожалуйста, сохраните номер заказа {order_ref} для предъявления поставщику при получении."
        )
        
        await bot.send_message(chat_id=consumer.telegram_id, text=consumer_message, reply_markup=get_main_keyboard())
        
        # Notify the vendor
        vendor_message = (
            f"🔔 Новый оплаченный заказ {order_ref}!\n\n"
            f"Детали заказа:\n"
            f"- Блюдо: {meal.name}\n"
            f"- Количество порций: {order.quantity}\n"
            f"- Время самовывоза: с {pickup_start} до {pickup_end}\n\n"
            f"Пожалуйста, подготовьте заказ к указанному времени самовывоза."
        )
        
        await bot.send_message(chat_id=vendor.telegram_id, text=vendor_message)
        
    except Exception as e:
        logging.error(f"Error sending order notifications: {e}")


# API handler for real payment gateway webhooks
async def process_payment_webhook(webhook_data, signature=None):
    """
    Process a webhook notification from the payment gateway.
    This function would be called from a web framework route handler in a real deployment.
    
    Args:
        webhook_data: The webhook payload as a dictionary
        signature: Optional webhook signature for verification
        
    Returns:
        bool: True if processing succeeded, False otherwise
    """
    try:
        # Import the payment gateway to avoid circular imports
        from .payment import payment_gateway
        
        # Process the webhook
        success = await payment_gateway.process_webhook(webhook_data)
        
        if success and webhook_data.get("status") == "completed":
            # Send notifications about the successful payment
            order_id = webhook_data.get("order_id")
            if order_id:
                await send_order_notifications(order_id)
                
        return success
        
    except Exception as e:
        logging.error(f"Error processing webhook: {e}")
        return False


@dp.message(Command("my_orders"))
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


# Add handler for the new orders button
@dp.message(lambda message: message.text == "🛒 Мои заказы")
async def button_my_orders(message: Message):
    """Handler for my orders button"""
    await cmd_my_orders(message)


async def main():
    """Main function to run the bot"""
    # Initialize database connection
    await init_db()
    
    try:
        # Start the bot
        await dp.start_polling(bot)
    finally:
        # Close database connection when done
        await close_db()


if __name__ == "__main__":
    """Entry point for the application"""
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped!")
