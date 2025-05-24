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


class PayoutStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


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
    EARNINGS_CALCULATED = "earnings_calculated"
    PAYOUT_REQUESTED = "payout_requested"
    PAYOUT_COMPLETED = "payout_completed"


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
    earnings = fields.ReverseRelation["VendorEarnings"]
    payout_requests = fields.ReverseRelation["PayoutRequest"]

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


class Commission(Model):
    """Commission model for tracking platform commission rates."""
    id = fields.IntField(pk=True)
    commission_rate = fields.DecimalField(max_digits=5, decimal_places=4, default=0.15)  # 15% default
    effective_from = fields.DatetimeField()
    effective_to = fields.DatetimeField(null=True)  # NULL means currently active
    description = fields.CharField(max_length=255, null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "commissions"


class VendorEarnings(Model):
    """Vendor earnings tracking model."""
    id = fields.IntField(pk=True)
    vendor = fields.ForeignKeyField("models.Vendor", related_name="earnings")
    order = fields.ForeignKeyField("models.Order", related_name="vendor_earnings")
    
    # Financial details
    gross_amount = fields.DecimalField(max_digits=10, decimal_places=2)  # Total order amount
    commission_rate = fields.DecimalField(max_digits=5, decimal_places=4)  # Commission rate at time of order
    commission_amount = fields.DecimalField(max_digits=10, decimal_places=2)  # Platform commission
    net_amount = fields.DecimalField(max_digits=10, decimal_places=2)  # Amount vendor receives
    
    # Tracking
    created_at = fields.DatetimeField(auto_now_add=True)
    period_year = fields.IntField()  # Year for easy filtering
    period_month = fields.IntField()  # Month (1-12) for easy filtering
    is_paid_out = fields.BooleanField(default=False)
    paid_out_at = fields.DatetimeField(null=True)

    class Meta:
        table = "vendor_earnings"
        indexes = [
            ("vendor", "period_year", "period_month"),
            ("is_paid_out",),
        ]


class PayoutRequest(Model):
    """Payout request tracking for vendors."""
    id = fields.IntField(pk=True)
    vendor = fields.ForeignKeyField("models.Vendor", related_name="payout_requests")
    
    # Payout details
    amount = fields.DecimalField(max_digits=10, decimal_places=2)
    currency = fields.CharField(max_length=3, default="KZT")  # Kazakhstani tenge
    status = fields.CharEnumField(PayoutStatus, default=PayoutStatus.PENDING)
    
    # Period covered
    period_year = fields.IntField()
    period_month = fields.IntField()
    
    # External processing
    external_transaction_id = fields.CharField(max_length=255, null=True)  # ID from external payout system
    external_notes = fields.TextField(null=True)  # Notes about external processing
    
    # Timestamps
    created_at = fields.DatetimeField(auto_now_add=True)
    processed_at = fields.DatetimeField(null=True)
    completed_at = fields.DatetimeField(null=True)

    class Meta:
        table = "payout_requests"
        unique_together = ("vendor", "period_year", "period_month")


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
