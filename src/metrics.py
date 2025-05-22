import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Tuple

from tortoise.functions import Count, Sum, Avg
from tortoise.expressions import Q

from .models import Metric, MetricType, Meal, Order, OrderStatus, Vendor, VendorStatus
from .config import ALMATY_TIMEZONE


logger = logging.getLogger(__name__)


async def track_metric(
    metric_type: MetricType,
    value: float = 1.0,
    entity_id: Optional[int] = None,
    user_id: Optional[int] = None,
    metadata: Optional[Dict] = None
) -> Metric:
    """
    Track a metric event in the database.
    
    Args:
        metric_type: Type of metric being tracked
        value: Numeric value for the metric (default is 1.0 for count-based metrics)
        entity_id: Optional ID of the related entity (meal, order, etc.)
        user_id: Optional Telegram user ID
        metadata: Optional additional contextual data as a dictionary
    
    Returns:
        The created Metric object
    """
    try:
        metric = await Metric.create(
            metric_type=metric_type,
            value=value,
            entity_id=entity_id,
            user_id=user_id,
            metadata=metadata
        )
        logger.info(f"Tracked metric: {metric_type.value}, value: {value}, entity_id: {entity_id}, user_id: {user_id}")
        return metric
    except Exception as e:
        logger.error(f"Error tracking metric {metric_type.value}: {str(e)}")
        # We don't want to break the application flow if metrics tracking fails
        return None


async def get_metrics_report(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    metric_types: Optional[List[MetricType]] = None
) -> Dict:
    """
    Generate a comprehensive metrics report for the specified time period.
    
    Args:
        start_date: Start date for the report (defaults to 30 days ago)
        end_date: End date for the report (defaults to now)
        metric_types: Optional list of metric types to include (defaults to all)
    
    Returns:
        Dictionary with metrics report data
    """
    # Set default date range if not provided
    if not end_date:
        end_date = datetime.now(ALMATY_TIMEZONE)
    elif end_date.tzinfo is None:
        # Make timezone-aware if it's not already
        end_date = end_date.replace(tzinfo=ALMATY_TIMEZONE)
        
    if not start_date:
        start_date = end_date - timedelta(days=30)
    elif start_date.tzinfo is None:
        # Make timezone-aware if it's not already
        start_date = start_date.replace(tzinfo=ALMATY_TIMEZONE)
    
    # Create base query with date filtering
    base_query = Q(timestamp__gte=start_date) & Q(timestamp__lte=end_date)
    
    # Add metric type filtering if specified
    if metric_types:
        metric_type_filter = Q(metric_type=metric_types[0])
        for m_type in metric_types[1:]:
            metric_type_filter |= Q(metric_type=m_type)
        base_query &= metric_type_filter
    
    # Collect report data
    report = {
        "time_period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        "summary": {},
        "details": {}
    }
    
    # Get counts for each metric type
    all_metrics = await Metric.filter(base_query).all()
    type_counts = {}
    for metric in all_metrics:
        metric_type = metric.metric_type.value
        if metric_type not in type_counts:
            type_counts[metric_type] = 0
        type_counts[metric_type] += 1
    
    report["summary"]["counts"] = type_counts
    
    # Calculate key conversion rates
    try:
        # Browse to purchase conversion
        browse_count = await Metric.filter(base_query & Q(metric_type=MetricType.MEAL_BROWSE)).count()
        view_count = await Metric.filter(base_query & Q(metric_type=MetricType.MEAL_VIEW)).count()
        order_created_count = await Metric.filter(base_query & Q(metric_type=MetricType.ORDER_CREATED)).count()
        order_paid_count = await Metric.filter(base_query & Q(metric_type=MetricType.ORDER_PAID)).count()
        order_completed_count = await Metric.filter(base_query & Q(metric_type=MetricType.ORDER_COMPLETED)).count()
        
        # Calculate conversion rates (avoiding division by zero)
        report["summary"]["conversion"] = {
            "browse_to_view": round((view_count / browse_count * 100) if browse_count > 0 else 0, 2),
            "view_to_order": round((order_created_count / view_count * 100) if view_count > 0 else 0, 2),
            "order_to_payment": round((order_paid_count / order_created_count * 100) if order_created_count > 0 else 0, 2),
            "payment_to_completion": round((order_completed_count / order_paid_count * 100) if order_paid_count > 0 else 0, 2),
            "overall_browse_to_purchase": round((order_paid_count / browse_count * 100) if browse_count > 0 else 0, 2)
        }
    except Exception as e:
        logger.error(f"Error calculating conversion rates: {str(e)}")
        report["summary"]["conversion"] = "Error calculating conversion rates"
    
    # Add user acquisition metrics
    try:
        users_registered = await Metric.filter(base_query & Q(metric_type=MetricType.USER_REGISTRATION)).count()
        vendors_registered = await Metric.filter(base_query & Q(metric_type=MetricType.VENDOR_REGISTRATION)).count()
        vendors_approved = await Metric.filter(base_query & Q(metric_type=MetricType.VENDOR_APPROVAL)).count()
        
        report["summary"]["acquisition"] = {
            "users_registered": users_registered,
            "vendors_registered": vendors_registered,
            "vendors_approved": vendors_approved,
        }
    except Exception as e:
        logger.error(f"Error calculating acquisition metrics: {str(e)}")
        report["summary"]["acquisition"] = "Error calculating acquisition metrics"
    
    # Add engagement metrics
    try:
        # Meals per vendor
        total_vendors = await Vendor.filter(status=VendorStatus.APPROVED).count()
        total_meals = await Meal.filter(is_active=True).count()
        meals_per_vendor = round(total_meals / total_vendors, 2) if total_vendors > 0 else 0
        
        # Average purchase value
        orders = await Order.filter(status=OrderStatus.PAID).prefetch_related('meal')
        if orders:
            total_value = sum(order.quantity * order.meal.price for order in orders)
            avg_order_value = round(float(total_value) / len(orders), 2) if orders else 0
        else:
            avg_order_value = 0
        
        report["summary"]["engagement"] = {
            "meals_per_vendor": meals_per_vendor,
            "avg_order_value": avg_order_value,
            "total_sales_value": float(total_value) if 'total_value' in locals() else 0
        }
    except Exception as e:
        logger.error(f"Error calculating engagement metrics: {str(e)}")
        report["summary"]["engagement"] = "Error calculating engagement metrics"
    
    # Add transaction metrics
    try:
        # Sales per day, calculated for each day in the range
        days = (end_date - start_date).days + 1
        daily_sales = []
        
        for day in range(days):
            day_start = start_date + timedelta(days=day)
            day_end = day_start + timedelta(days=1)
            day_orders = await Metric.filter(
                Q(timestamp__gte=day_start) & 
                Q(timestamp__lt=day_end) & 
                Q(metric_type=MetricType.ORDER_PAID)
            ).count()
            
            daily_sales.append({
                "date": day_start.date().isoformat(),
                "orders": day_orders
            })
        
        report["details"]["daily_sales"] = daily_sales
    except Exception as e:
        logger.error(f"Error calculating daily sales metrics: {str(e)}")
        report["details"]["daily_sales"] = "Error calculating daily sales metrics"
    
    return report


async def get_most_viewed_meals(limit: int = 10) -> List[Tuple[Meal, int]]:
    """
    Get the most viewed meals based on MEAL_VIEW metrics.
    
    Args:
        limit: Maximum number of meals to return
        
    Returns:
        List of (Meal, view_count) tuples
    """
    # Get meal IDs and their view counts
    meal_views = {}
    view_metrics = await Metric.filter(metric_type=MetricType.MEAL_VIEW).all()
    
    for metric in view_metrics:
        if metric.entity_id:
            meal_id = metric.entity_id
            if meal_id not in meal_views:
                meal_views[meal_id] = 0
            meal_views[meal_id] += 1
    
    # Sort meal IDs by view count (descending)
    sorted_meal_ids = sorted(meal_views.keys(), key=lambda x: meal_views[x], reverse=True)[:limit]
    
    # Get the actual Meal objects
    result = []
    for meal_id in sorted_meal_ids:
        meal = await Meal.filter(id=meal_id).first()
        if meal:
            result.append((meal, meal_views[meal_id]))
    
    return result


async def get_metrics_dashboard_data() -> Dict:
    """
    Get summarized metrics data for a dashboard display.
    
    Returns:
        Dictionary with key metrics for dashboard display
    """
    try:
        # Get current time in Almaty timezone
        current_time = datetime.now(ALMATY_TIMEZONE)
        
        # Get counts
        total_users = await Metric.filter(metric_type=MetricType.USER_REGISTRATION).count()
        total_vendors = await Vendor.all().count()
        approved_vendors = await Vendor.filter(status=VendorStatus.APPROVED).count()
        total_meals = await Meal.all().count()
        active_meals = await Meal.filter(is_active=True, quantity__gt=0, pickup_end_time__gt=current_time).count()
        total_orders = await Order.all().count()
        paid_orders = await Order.filter(status=OrderStatus.PAID).count()
        completed_orders = await Order.filter(status=OrderStatus.COMPLETED).count()
        
        # Calculate GMV (Gross Merchandise Value)
        gmv = 0
        orders = await Order.filter(status__in=[OrderStatus.PAID, OrderStatus.COMPLETED]).prefetch_related('meal')
        for order in orders:
            gmv += float(order.meal.price) * order.quantity
        
        # Get 7-day metrics
        week_ago = datetime.now(ALMATY_TIMEZONE) - timedelta(days=7)
        week_metrics = await get_metrics_report(start_date=week_ago)
        
        # Prepare dashboard data
        dashboard = {
            "overview": {
                "total_users": total_users,
                "total_vendors": total_vendors,
                "approved_vendors": approved_vendors,
                "active_meals": active_meals,
                "total_meals_ever": total_meals,
                "paid_orders": paid_orders,
                "completed_orders": completed_orders,
                "gmv_total": round(gmv, 2)
            },
            "weekly": {
                "conversion_rates": week_metrics["summary"].get("conversion", {}),
                "daily_sales": week_metrics["details"].get("daily_sales", [])
            }
        }
        
        return dashboard
    except Exception as e:
        logger.error(f"Error generating metrics dashboard: {str(e)}")
        return {"error": f"Could not generate metrics dashboard: {str(e)}"}


async def get_peak_hours_analysis() -> Dict:
    """
    Analyze peak activity hours based on metric timestamps.
    
    Returns:
        Dictionary with hourly activity breakdown
    """
    try:
        # Get all metrics from the last 30 days
        thirty_days_ago = datetime.now(ALMATY_TIMEZONE) - timedelta(days=30)
        metrics = await Metric.filter(timestamp__gte=thirty_days_ago).all()
        
        # Group by hour of day
        hourly_activity = {hour: 0 for hour in range(24)}
        
        for metric in metrics:
            # Convert to Almaty timezone if needed
            metric_time = metric.timestamp
            if metric_time.tzinfo is None:
                metric_time = metric_time.replace(tzinfo=ALMATY_TIMEZONE)
            else:
                metric_time = metric_time.astimezone(ALMATY_TIMEZONE)
            
            hour = metric_time.hour
            hourly_activity[hour] += 1
        
        # Find peak hours
        sorted_hours = sorted(hourly_activity.items(), key=lambda x: x[1], reverse=True)
        peak_hours = sorted_hours[:3]  # Top 3 hours
        
        return {
            "hourly_breakdown": hourly_activity,
            "peak_hours": peak_hours,
            "total_activity": sum(hourly_activity.values())
        }
    except Exception as e:
        logger.error(f"Error analyzing peak hours: {str(e)}")
        return {"error": str(e)}


async def get_user_activity_patterns() -> Dict:
    """
    Analyze user activity patterns and engagement metrics.
    
    Returns:
        Dictionary with user activity analysis
    """
    try:
        # Get activity for the last 30 days
        thirty_days_ago = datetime.now(ALMATY_TIMEZONE) - timedelta(days=30)
        
        # Get all user activities
        user_metrics = {}
        metrics = await Metric.filter(
            timestamp__gte=thirty_days_ago,
            user_id__isnull=False
        ).all()
        
        for metric in metrics:
            user_id = metric.user_id
            if user_id not in user_metrics:
                user_metrics[user_id] = {
                    "total_actions": 0,
                    "action_types": {},
                    "last_activity": metric.timestamp
                }
            
            user_metrics[user_id]["total_actions"] += 1
            
            # Track action types
            action_type = metric.metric_type.value
            if action_type not in user_metrics[user_id]["action_types"]:
                user_metrics[user_id]["action_types"][action_type] = 0
            user_metrics[user_id]["action_types"][action_type] += 1
            
            # Update last activity
            if metric.timestamp > user_metrics[user_id]["last_activity"]:
                user_metrics[user_id]["last_activity"] = metric.timestamp
        
        # Calculate engagement statistics
        if user_metrics:
            total_users = len(user_metrics)
            actions_per_user = [data["total_actions"] for data in user_metrics.values()]
            avg_actions_per_user = sum(actions_per_user) / total_users
            
            # Find power users (top 10% by activity)
            sorted_users = sorted(user_metrics.items(), key=lambda x: x[1]["total_actions"], reverse=True)
            power_user_count = max(1, total_users // 10)
            power_users = sorted_users[:power_user_count]
            
            # Calculate active users (users with activity in last 7 days)
            week_ago = datetime.now(ALMATY_TIMEZONE) - timedelta(days=7)
            active_users = sum(1 for data in user_metrics.values() 
                             if data["last_activity"] >= week_ago)
            
            return {
                "total_users_active": total_users,
                "avg_actions_per_user": round(avg_actions_per_user, 2),
                "power_users_count": len(power_users),
                "active_last_week": active_users,
                "engagement_rate": round((active_users / total_users * 100), 2) if total_users > 0 else 0,
                "top_power_users": [(user_id, data["total_actions"]) for user_id, data in power_users[:5]]
            }
        else:
            return {
                "total_users_active": 0,
                "avg_actions_per_user": 0,
                "power_users_count": 0,
                "active_last_week": 0,
                "engagement_rate": 0,
                "top_power_users": []
            }
            
    except Exception as e:
        logger.error(f"Error analyzing user activity patterns: {str(e)}")
        return {"error": str(e)}


async def get_conversion_funnel_detailed() -> Dict:
    """
    Get detailed conversion funnel analysis with dropoff points.
    
    Returns:
        Dictionary with detailed funnel analysis
    """
    try:
        # Get metrics for the last 30 days
        thirty_days_ago = datetime.now(ALMATY_TIMEZONE) - timedelta(days=30)
        
        # Count each step in the funnel
        funnel_steps = {
            "browse": await Metric.filter(
                timestamp__gte=thirty_days_ago,
                metric_type=MetricType.MEAL_BROWSE
            ).count(),
            "view": await Metric.filter(
                timestamp__gte=thirty_days_ago,
                metric_type=MetricType.MEAL_VIEW
            ).count(),
            "order_created": await Metric.filter(
                timestamp__gte=thirty_days_ago,
                metric_type=MetricType.ORDER_CREATED
            ).count(),
            "order_paid": await Metric.filter(
                timestamp__gte=thirty_days_ago,
                metric_type=MetricType.ORDER_PAID
            ).count(),
            "order_completed": await Metric.filter(
                timestamp__gte=thirty_days_ago,
                metric_type=MetricType.ORDER_COMPLETED
            ).count()
        }
        
        # Calculate conversion rates and dropoff
        conversions = {}
        dropoffs = {}
        
        steps = list(funnel_steps.keys())
        for i in range(len(steps) - 1):
            current_step = steps[i]
            next_step = steps[i + 1]
            
            current_count = funnel_steps[current_step]
            next_count = funnel_steps[next_step]
            
            if current_count > 0:
                conversion_rate = round((next_count / current_count) * 100, 2)
                dropoff_rate = round(100 - conversion_rate, 2)
                dropoff_count = current_count - next_count
            else:
                conversion_rate = 0
                dropoff_rate = 0
                dropoff_count = 0
            
            conversions[f"{current_step}_to_{next_step}"] = conversion_rate
            dropoffs[f"{current_step}_to_{next_step}"] = {
                "rate": dropoff_rate,
                "count": dropoff_count
            }
        
        return {
            "funnel_counts": funnel_steps,
            "conversions": conversions,
            "dropoffs": dropoffs,
            "total_entered_funnel": funnel_steps["browse"]
        }
        
    except Exception as e:
        logger.error(f"Error analyzing conversion funnel: {str(e)}")
        return {"error": str(e)}


async def get_vendor_performance_metrics() -> Dict:
    """
    Analyze vendor performance metrics.
    
    Returns:
        Dictionary with vendor performance data
    """
    try:
        # Get all approved vendors with their meals and orders
        vendors = await Vendor.filter(status=VendorStatus.APPROVED).prefetch_related('meals', 'meals__orders').all()
        
        vendor_stats = []
        
        for vendor in vendors:
            # Calculate metrics for each vendor
            total_meals = len([meal for meal in vendor.meals if meal.is_active])
            total_orders = sum(len(meal.orders) for meal in vendor.meals)
            paid_orders = sum(len([order for order in meal.orders if order.status in [OrderStatus.PAID, OrderStatus.COMPLETED]]) for meal in vendor.meals)
            
            # Calculate revenue
            total_revenue = 0
            for meal in vendor.meals:
                for order in meal.orders:
                    if order.status in [OrderStatus.PAID, OrderStatus.COMPLETED]:
                        total_revenue += float(meal.price) * order.quantity
            
            # Calculate average meal price
            active_meals = [meal for meal in vendor.meals if meal.is_active]
            avg_meal_price = sum(float(meal.price) for meal in active_meals) / len(active_meals) if active_meals else 0
            
            vendor_stats.append({
                "vendor_id": vendor.telegram_id,
                "vendor_name": vendor.name,
                "total_meals": total_meals,
                "total_orders": total_orders,
                "paid_orders": paid_orders,
                "total_revenue": round(total_revenue, 2),
                "avg_meal_price": round(avg_meal_price, 2),
                "orders_per_meal": round(paid_orders / total_meals, 2) if total_meals > 0 else 0
            })
        
        # Sort by revenue
        vendor_stats.sort(key=lambda x: x["total_revenue"], reverse=True)
        
        # Calculate aggregate statistics
        total_vendors = len(vendor_stats)
        total_revenue_all = sum(v["total_revenue"] for v in vendor_stats)
        avg_revenue_per_vendor = total_revenue_all / total_vendors if total_vendors > 0 else 0
        
        return {
            "vendor_performance": vendor_stats[:10],  # Top 10 vendors
            "summary": {
                "total_vendors": total_vendors,
                "total_revenue": round(total_revenue_all, 2),
                "avg_revenue_per_vendor": round(avg_revenue_per_vendor, 2)
            }
        }
        
    except Exception as e:
        logger.error(f"Error analyzing vendor performance: {str(e)}")
        return {"error": str(e)} 