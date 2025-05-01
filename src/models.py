from tortoise import fields
from tortoise.models import Model
from enum import Enum


class VendorStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class OrderStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Vendor(Model):
    """Vendor model representing food businesses."""
    id = fields.IntField(pk=True)
    telegram_id = fields.BigIntField(unique=True)
    name = fields.CharField(max_length=255)
    contact_phone = fields.CharField(max_length=20, null=True)
    status = fields.CharEnumField(VendorStatus, default=VendorStatus.PENDING)
    created_at = fields.DatetimeField(auto_now_add=True)

    # Relationships
    meals = fields.ReverseRelation["Meal"]

    class Meta:
        table = "vendors"


class Consumer(Model):
    """Consumer model representing users who purchase meals."""
    id = fields.IntField(pk=True)
    telegram_id = fields.BigIntField(unique=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    # Relationships
    orders = fields.ReverseRelation["Order"]

    class Meta:
        table = "consumers"


class Meal(Model):
    """Meal model representing food items listed by vendors."""
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=255)
    description = fields.TextField()
    price = fields.DecimalField(max_digits=10, decimal_places=2)
    quantity = fields.IntField(default=1)
    pickup_start_time = fields.DatetimeField()
    pickup_end_time = fields.DatetimeField()
    location_address = fields.TextField()
    location_latitude = fields.FloatField(null=True)
    location_longitude = fields.FloatField(null=True)
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    # Relationships
    vendor = fields.ForeignKeyField("models.Vendor", related_name="meals")
    orders = fields.ReverseRelation["Order"]

    class Meta:
        table = "meals"


class Order(Model):
    """Order model representing purchases made by consumers."""
    id = fields.IntField(pk=True)
    status = fields.CharEnumField(OrderStatus, default=OrderStatus.PENDING)
    payment_id = fields.CharField(max_length=255, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    completed_at = fields.DatetimeField(null=True)

    # Relationships
    consumer = fields.ForeignKeyField("models.Consumer", related_name="orders")
    meal = fields.ForeignKeyField("models.Meal", related_name="orders")

    class Meta:
        table = "orders"
