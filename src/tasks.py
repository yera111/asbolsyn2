import asyncio
import logging
import datetime

from .models import Meal, Order, OrderStatus
from .config import ALMATY_TIMEZONE

logger = logging.getLogger(__name__)

async def deactivate_expired_meals():
    """
    Deactivate meals where the pickup window has ended.
    This task should run periodically to check and update meal statuses.
    """
    try:
        # Get current time in Almaty timezone
        now = datetime.datetime.now(ALMATY_TIMEZONE)
        
        # Find all active meals with pickup_end_time in the past
        expired_meals = await Meal.filter(is_active=True, pickup_end_time__lt=now)
        
        if expired_meals:
            count = len(expired_meals)
            logger.info(f"Found {count} expired meals to deactivate")
            
            # Deactivate each expired meal
            for meal in expired_meals:
                meal.is_active = False
                await meal.save()
                logger.info(f"Deactivated meal: {meal.id} - {meal.name}")
            
            logger.info(f"Successfully deactivated {count} expired meals")
        else:
            logger.info("No expired meals found to deactivate")
            
    except Exception as e:
        logger.error(f"Error in deactivate_expired_meals task: {e}")


async def cleanup_expired_orders():
    """
    Automatically cancel orders that have been in PENDING status for more than 30 minutes.
    This prevents accumulation of unpaid orders and frees up meal quantities.
    """
    try:
        # Get current time in Almaty timezone
        now = datetime.datetime.now(ALMATY_TIMEZONE)
        
        # Calculate the cutoff time (30 minutes ago)
        cutoff_time = now - datetime.timedelta(minutes=30)
        
        # Find all PENDING orders older than 30 minutes
        expired_orders = await Order.filter(
            status=OrderStatus.PENDING,
            created_at__lt=cutoff_time
        ).prefetch_related('meal')
        
        if expired_orders:
            count = len(expired_orders)
            logger.info(f"Found {count} expired pending orders to cancel")
            
            # Cancel each expired order
            for order in expired_orders:
                order.status = OrderStatus.CANCELLED
                await order.save()
                
                # Log the cancellation
                logger.info(f"Auto-cancelled expired order: {order.id} (meal: {order.meal.name})")
            
            logger.info(f"Successfully cancelled {count} expired pending orders")
        else:
            logger.info("No expired pending orders found")
            
    except Exception as e:
        logger.error(f"Error in cleanup_expired_orders task: {e}")

# Dictionary of scheduled tasks for easy access
scheduled_tasks = {
    "deactivate_expired_meals": deactivate_expired_meals,
    "cleanup_expired_orders": cleanup_expired_orders
} 