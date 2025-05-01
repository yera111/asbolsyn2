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
from .models import Consumer, Vendor, VendorStatus, Meal

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher with FSM storage
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Russian text templates
TEXT = {
    "welcome": "Добро пожаловать в As Bolsyn! Этот бот поможет вам найти и приобрести блюда от местных заведений по сниженным ценам.",
    "help": "Доступные команды:\n/start - Запустить бот\n/help - Показать эту справку\n/register_vendor - Зарегистрироваться как поставщик\n/add_meal - Добавить блюдо (только для поставщиков)\n/my_meals - Просмотреть мои блюда (только для поставщиков)\n/browse_meals - Просмотреть доступные блюда\n/meals_nearby - Найти блюда поблизости\n/view_meal <id> - Посмотреть детали блюда",
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
    "meal_id_invalid": "Неверный ID блюда. Пожалуйста, используйте числовой ID."
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


@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Handler for /start command"""
    # Register user if not already registered
    user_id = message.from_user.id
    consumer, created = await Consumer.get_or_create(telegram_id=user_id)
    
    await message.answer(TEXT["welcome"])


@dp.message(Command("help"))
async def cmd_help(message: Message):
    """Handler for /help command"""
    await message.answer(TEXT["help"])


@dp.message(Command("register_vendor"))
async def cmd_register_vendor(message: Message, state: FSMContext):
    """Handler to start vendor registration process"""
    user_id = message.from_user.id
    
    # Check if already registered
    existing_vendor = await Vendor.filter(telegram_id=user_id).first()
    if existing_vendor:
        await message.answer(TEXT["vendor_already_registered"].format(status=existing_vendor.status.value))
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
    await message.answer(TEXT["vendor_registered"])
    
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
        reply_markup=ReplyKeyboardRemove()
    )


@dp.message(Command("my_meals"))
async def cmd_my_meals(message: Message):
    """Handler to view vendor's meals"""
    user_id = message.from_user.id
    
    # Check if user is a registered vendor
    vendor = await Vendor.filter(telegram_id=user_id).first()
    if not vendor:
        await message.answer(TEXT["not_vendor"])
        return
    
    # Get all active meals for this vendor
    meals = await Meal.filter(vendor=vendor, is_active=True)
    
    if not meals:
        await message.answer(TEXT["my_meals_empty"])
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
    
    await message.answer(response)


@dp.message(Command("delete_meal"))
async def cmd_delete_meal(message: Message):
    """Handler for vendor to delete a meal"""
    user_id = message.from_user.id
    
    # Check if user is a registered vendor
    vendor = await Vendor.filter(telegram_id=user_id).first()
    if not vendor:
        await message.answer(TEXT["not_vendor"])
        return
    
    # Get meal ID from command arguments
    command_parts = message.text.split()
    if len(command_parts) != 2:
        await message.answer("Используйте формат: /delete_meal ID")
        return
    
    try:
        meal_id = int(command_parts[1])
        
        # Find the meal, ensuring it belongs to this vendor
        meal = await Meal.filter(id=meal_id, vendor=vendor, is_active=True).first()
        
        if not meal:
            await message.answer(TEXT["meal_not_found"])
            return
        
        # Deactivate the meal (soft delete)
        meal.is_active = False
        await meal.save()
        
        # Notify vendor
        await message.answer(TEXT["meal_delete_success"])
    
    except (ValueError, TypeError):
        await message.answer("Неверный формат ID. Используйте числовой ID блюда.")


@dp.message(Command("browse_meals"))
async def cmd_browse_meals(message: Message):
    """Handler for /browse_meals command - Shows all available meals"""
    user_id = message.from_user.id
    
    # Register user if not already registered
    consumer, created = await Consumer.get_or_create(telegram_id=user_id)
    
    # Get all active meals with quantity > 0, ordered by creation date (newest first)
    meals = await Meal.filter(is_active=True, quantity__gt=0).prefetch_related('vendor').order_by('-created_at')
    
    if not meals:
        await message.answer(TEXT["browse_meals_empty"])
        return
    
    # Format the list of meals
    response = TEXT["browse_meals_header"]
    
    for meal in meals:
        # Format pickup times
        pickup_start = meal.pickup_start_time.strftime('%H:%M')
        pickup_end = meal.pickup_end_time.strftime('%H:%M')
        
        # Add meal to response
        response += TEXT["browse_meals_item"].format(
            id=meal.id,
            name=meal.name,
            price=meal.price,
            vendor=meal.vendor.name,
            quantity=meal.quantity,
            pickup_start=pickup_start,
            pickup_end=pickup_end
        ) + "\n\n"
    
    await message.answer(response)


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
        await message.answer(TEXT["meal_invalid_location"])
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
        await message.answer(TEXT["meals_nearby_empty"].format(radius=radius), reply_markup=ReplyKeyboardRemove())
        return
    
    # Format the list of meals
    response = TEXT["meals_nearby_header"]
    
    for meal in nearby_meals:
        # Calculate distance
        distance = calculate_distance(location.latitude, location.longitude, meal.location_latitude, meal.location_longitude)
        
        # Format pickup times
        pickup_start = meal.pickup_start_time.strftime('%H:%M')
        pickup_end = meal.pickup_end_time.strftime('%H:%M')
        
        # Add meal to response
        response += TEXT["meals_nearby_item"].format(
            id=meal.id,
            name=meal.name,
            price=meal.price,
            distance=distance,
            vendor=meal.vendor.name,
            quantity=meal.quantity,
            pickup_start=pickup_start,
            pickup_end=pickup_end
        ) + "\n\n"
    
    await message.answer(response, reply_markup=ReplyKeyboardRemove())


@dp.message(Command("view_meal"))
async def cmd_view_meal(message: Message):
    """Handler for /view_meal command - Shows detailed meal information"""
    user_id = message.from_user.id
    
    # Register user if not already registered
    consumer, created = await Consumer.get_or_create(telegram_id=user_id)
    
    # Get meal ID from command arguments
    command_parts = message.text.split()
    if len(command_parts) != 2:
        await message.answer("Используйте формат: /view_meal ID")
        return
    
    try:
        meal_id = int(command_parts[1])
        
        # Find the meal
        meal = await Meal.filter(id=meal_id, is_active=True, quantity__gt=0).prefetch_related('vendor').first()
        
        if not meal:
            await message.answer(TEXT["meal_not_found"])
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
        
        # Create inline keyboard for buying
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text=TEXT["meal_view_button"], callback_data=f"buy_meal:{meal.id}")]
        ])
        
        await message.answer(response, reply_markup=keyboard)
    
    except (ValueError, TypeError):
        await message.answer(TEXT["meal_id_invalid"])


@dp.callback_query(lambda c: c.data and c.data.startswith('buy_meal:'))
async def process_buy_callback(callback_query: CallbackQuery):
    """Handler for buy meal button callback"""
    # Extract meal ID from callback data
    meal_id = int(callback_query.data.split(':')[1])
    
    # This is a placeholder for the actual payment flow to be implemented in Step 4
    await callback_query.answer("Функциональность покупки будет доступна в ближайшее время!")
    
    # Optional: Display a message to inform user that the complete payment flow is coming soon
    await callback_query.message.answer("Полный процесс покупки будет реализован в ближайшее время. Спасибо за интерес!")


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
