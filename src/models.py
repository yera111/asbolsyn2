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


class MetricType(str, Enum):
    USER_REGISTRATION = "user_registration"
    VENDOR_REGISTRATION = "vendor_registration"
    VENDOR_APPROVAL = "vendor_approval"
    MEAL_CREATION = "meal_creation"
    MEAL_VIEW = "meal_view"
    MEAL_BROWSE = "meal_browse"
    NEARBY_SEARCH = "nearby_search"
    ORDER_CREATED = "order_created"
    ORDER_PAID = "order_paid"
    ORDER_COMPLETED = "order_completed"
    ORDER_CANCELLED = "order_cancelled"
    PORTION_SELECTION = "portion_selection"


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
    quantity = fields.IntField(default=1)  # Number of portions ordered
    created_at = fields.DatetimeField(auto_now_add=True)
    completed_at = fields.DatetimeField(null=True)

    # Relationships
    consumer = fields.ForeignKeyField("models.Consumer", related_name="orders")
    meal = fields.ForeignKeyField("models.Meal", related_name="orders")

    class Meta:
        table = "orders"


class Metric(Model):
    """Metrics model for tracking key performance indicators."""
    id = fields.IntField(pk=True)
    metric_type = fields.CharEnumField(MetricType)
    value = fields.FloatField(default=1.0)  # Default is 1.0 for count-based metrics
    entity_id = fields.IntField(null=True)  # Optional ID of related entity (meal, order, etc.)
    user_id = fields.BigIntField(null=True)  # Optional Telegram user ID
    metadata = fields.JSONField(null=True)  # Additional contextual data
    timestamp = fields.DatetimeField(auto_now_add=True)
    
    class Meta:
        table = "metrics"
