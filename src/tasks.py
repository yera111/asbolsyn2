import asyncio
import logging
import datetime

from .models import Meal
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

# Dictionary of scheduled tasks for easy access
scheduled_tasks = {
    "deactivate_expired_meals": deactivate_expired_meals
} 