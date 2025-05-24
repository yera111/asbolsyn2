"""
Vendor earnings tracking and management module.
Handles commission calculations, earnings tracking, and payout requests.
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional
from dateutil.relativedelta import relativedelta

from src.models import (
    Vendor, Order, VendorEarnings, Commission, PayoutRequest, 
    OrderStatus, PayoutStatus, MetricType
)
from src.config import get_current_almaty_time
from src.metrics import track_metric

logger = logging.getLogger(__name__)


async def get_current_commission_rate() -> Decimal:
    """
    Get the current active commission rate.
    
    Returns:
        Current commission rate as Decimal
    """
    try:
        current_time = get_current_almaty_time()
        
        # Find active commission rate
        commission = await Commission.filter(
            effective_from__lte=current_time
        ).filter(
            effective_to__isnull=True
        ).first()
        
        if not commission:
            # If no commission found, try to get the latest one
            commission = await Commission.all().order_by('-effective_from').first()
            
        if commission:
            return commission.commission_rate
        else:
            # Default commission rate if none configured
            logger.warning("No commission rate configured, using default 15%")
            return Decimal('0.15')
            
    except Exception as e:
        logger.error(f"Error getting commission rate: {str(e)}")
        return Decimal('0.15')  # Default fallback


async def calculate_and_record_earnings(order: Order) -> Optional[VendorEarnings]:
    """
    Calculate and record vendor earnings for a completed order.
    
    Args:
        order: The completed order
        
    Returns:
        VendorEarnings record if successful, None otherwise
    """
    try:
        # Get order with related data
        await order.fetch_related('meal', 'meal__vendor')
        
        if order.status != OrderStatus.COMPLETED:
            logger.warning(f"Order {order.id} is not completed, status: {order.status}")
            return None
            
        # Check if earnings already recorded
        existing_earnings = await VendorEarnings.filter(order=order).first()
        if existing_earnings:
            logger.info(f"Earnings already recorded for order {order.id}")
            return existing_earnings
            
        # Calculate earnings
        gross_amount = order.meal.price * order.quantity
        commission_rate = await get_current_commission_rate()
        commission_amount = gross_amount * commission_rate
        net_amount = gross_amount - commission_amount
        
        # Get period info
        completed_date = order.completed_at or order.created_at
        period_year = completed_date.year
        period_month = completed_date.month
        
        # Create earnings record
        earnings = await VendorEarnings.create(
            vendor=order.meal.vendor,
            order=order,
            gross_amount=gross_amount,
            commission_rate=commission_rate,
            commission_amount=commission_amount,
            net_amount=net_amount,
            period_year=period_year,
            period_month=period_month
        )
        
        # Track metrics
        await track_metric(
            metric_type=MetricType.EARNINGS_CALCULATED,
            entity_id=earnings.id,
            user_id=order.meal.vendor.telegram_id,
            value=float(net_amount),
            metadata={
                "order_id": order.id,
                "vendor_id": order.meal.vendor.id,
                "gross_amount": float(gross_amount),
                "commission_amount": float(commission_amount),
                "commission_rate": float(commission_rate),
                "period_year": period_year,
                "period_month": period_month
            }
        )
        
        logger.info(f"Recorded earnings for order {order.id}: {net_amount} KZT (gross: {gross_amount}, commission: {commission_amount})")
        return earnings
        
    except Exception as e:
        logger.error(f"Error calculating earnings for order {order.id}: {str(e)}")
        return None


async def get_vendor_monthly_earnings(vendor: Vendor, year: int, month: int) -> Dict:
    """
    Get vendor earnings summary for a specific month.
    
    Args:
        vendor: The vendor
        year: Year (e.g., 2024)
        month: Month (1-12)
        
    Returns:
        Dictionary with earnings summary
    """
    try:
        earnings = await VendorEarnings.filter(
            vendor=vendor,
            period_year=year,
            period_month=month
        ).prefetch_related('order').all()
        
        if not earnings:
            return {
                "vendor_id": vendor.id,
                "vendor_name": vendor.name,
                "period": f"{year}-{month:02d}",
                "total_orders": 0,
                "total_gross": Decimal('0.00'),
                "total_commission": Decimal('0.00'),
                "total_net": Decimal('0.00'),
                "is_paid_out": False,
                "earnings": []
            }
        
        # Calculate totals
        total_gross = sum(e.gross_amount for e in earnings)
        total_commission = sum(e.commission_amount for e in earnings)
        total_net = sum(e.net_amount for e in earnings)
        is_paid_out = all(e.is_paid_out for e in earnings)
        
        return {
            "vendor_id": vendor.id,
            "vendor_name": vendor.name,
            "period": f"{year}-{month:02d}",
            "total_orders": len(earnings),
            "total_gross": total_gross,
            "total_commission": total_commission,
            "total_net": total_net,
            "is_paid_out": is_paid_out,
            "earnings": [
                {
                    "order_id": e.order.id,
                    "gross_amount": e.gross_amount,
                    "commission_amount": e.commission_amount,
                    "net_amount": e.net_amount,
                    "created_at": e.created_at.isoformat(),
                    "is_paid_out": e.is_paid_out
                }
                for e in earnings
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting vendor monthly earnings: {str(e)}")
        return {"error": str(e)}


async def get_vendor_unpaid_earnings(vendor: Vendor) -> Dict:
    """
    Get all unpaid earnings for a vendor.
    
    Args:
        vendor: The vendor
        
    Returns:
        Dictionary with unpaid earnings by month
    """
    try:
        unpaid_earnings = await VendorEarnings.filter(
            vendor=vendor,
            is_paid_out=False
        ).order_by('period_year', 'period_month').all()
        
        if not unpaid_earnings:
            return {
                "vendor_id": vendor.id,
                "vendor_name": vendor.name,
                "total_unpaid": Decimal('0.00'),
                "periods": []
            }
        
        # Group by period
        periods = {}
        for earning in unpaid_earnings:
            period_key = f"{earning.period_year}-{earning.period_month:02d}"
            if period_key not in periods:
                periods[period_key] = {
                    "year": earning.period_year,
                    "month": earning.period_month,
                    "orders": 0,
                    "total_net": Decimal('0.00')
                }
            periods[period_key]["orders"] += 1
            periods[period_key]["total_net"] += earning.net_amount
        
        total_unpaid = sum(p["total_net"] for p in periods.values())
        
        return {
            "vendor_id": vendor.id,
            "vendor_name": vendor.name,
            "total_unpaid": total_unpaid,
            "periods": list(periods.values())
        }
        
    except Exception as e:
        logger.error(f"Error getting unpaid earnings: {str(e)}")
        return {"error": str(e)}


async def create_monthly_payout_request(vendor: Vendor, year: int, month: int) -> Optional[PayoutRequest]:
    """
    Create a payout request for a vendor's monthly earnings.
    
    Args:
        vendor: The vendor
        year: Year
        month: Month
        
    Returns:
        PayoutRequest if successful, None otherwise
    """
    try:
        # Check if payout request already exists
        existing_request = await PayoutRequest.filter(
            vendor=vendor,
            period_year=year,
            period_month=month
        ).first()
        
        if existing_request:
            logger.info(f"Payout request already exists for {vendor.name} {year}-{month:02d}")
            return existing_request
        
        # Get monthly earnings
        earnings_summary = await get_vendor_monthly_earnings(vendor, year, month)
        
        if earnings_summary.get("total_net", 0) <= 0:
            logger.warning(f"No earnings to payout for {vendor.name} {year}-{month:02d}")
            return None
        
        # Create payout request
        payout_request = await PayoutRequest.create(
            vendor=vendor,
            amount=earnings_summary["total_net"],
            period_year=year,
            period_month=month
        )
        
        # Track metrics
        await track_metric(
            metric_type=MetricType.PAYOUT_REQUESTED,
            entity_id=payout_request.id,
            user_id=vendor.telegram_id,
            value=float(earnings_summary["total_net"]),
            metadata={
                "vendor_id": vendor.id,
                "period_year": year,
                "period_month": month,
                "total_orders": earnings_summary["total_orders"]
            }
        )
        
        logger.info(f"Created payout request for {vendor.name}: {earnings_summary['total_net']} KZT for {year}-{month:02d}")
        return payout_request
        
    except Exception as e:
        logger.error(f"Error creating payout request: {str(e)}")
        return None


async def mark_earnings_as_paid(vendor: Vendor, year: int, month: int, external_transaction_id: str = None) -> bool:
    """
    Mark all earnings for a specific month as paid out.
    
    Args:
        vendor: The vendor
        year: Year
        month: Month
        external_transaction_id: Optional external transaction ID
        
    Returns:
        True if successful, False otherwise
    """
    try:
        current_time = get_current_almaty_time()
        
        # Update earnings records
        earnings = await VendorEarnings.filter(
            vendor=vendor,
            period_year=year,
            period_month=month,
            is_paid_out=False
        ).all()
        
        if not earnings:
            logger.warning(f"No unpaid earnings found for {vendor.name} {year}-{month:02d}")
            return False
        
        # Mark as paid
        for earning in earnings:
            earning.is_paid_out = True
            earning.paid_out_at = current_time
            await earning.save()
        
        # Update payout request
        payout_request = await PayoutRequest.filter(
            vendor=vendor,
            period_year=year,
            period_month=month
        ).first()
        
        if payout_request:
            payout_request.status = PayoutStatus.COMPLETED
            payout_request.completed_at = current_time
            if external_transaction_id:
                payout_request.external_transaction_id = external_transaction_id
            await payout_request.save()
            
            # Track metrics
            await track_metric(
                metric_type=MetricType.PAYOUT_COMPLETED,
                entity_id=payout_request.id,
                user_id=vendor.telegram_id,
                value=float(payout_request.amount),
                metadata={
                    "vendor_id": vendor.id,
                    "period_year": year,
                    "period_month": month,
                    "external_transaction_id": external_transaction_id
                }
            )
        
        logger.info(f"Marked earnings as paid for {vendor.name} {year}-{month:02d}: {len(earnings)} earnings records")
        return True
        
    except Exception as e:
        logger.error(f"Error marking earnings as paid: {str(e)}")
        return False


async def get_monthly_platform_revenue(year: int, month: int) -> Dict:
    """
    Get total platform commission revenue for a specific month.
    
    Args:
        year: Year
        month: Month
        
    Returns:
        Dictionary with platform revenue summary
    """
    try:
        earnings = await VendorEarnings.filter(
            period_year=year,
            period_month=month
        ).prefetch_related('vendor').all()
        
        if not earnings:
            return {
                "period": f"{year}-{month:02d}",
                "total_orders": 0,
                "total_gross_revenue": Decimal('0.00'),
                "total_commission": Decimal('0.00'),
                "total_vendor_earnings": Decimal('0.00'),
                "unique_vendors": 0
            }
        
        total_gross = sum(e.gross_amount for e in earnings)
        total_commission = sum(e.commission_amount for e in earnings)
        total_vendor_earnings = sum(e.net_amount for e in earnings)
        unique_vendors = len(set(e.vendor.id for e in earnings))
        
        return {
            "period": f"{year}-{month:02d}",
            "total_orders": len(earnings),
            "total_gross_revenue": total_gross,
            "total_commission": total_commission,
            "total_vendor_earnings": total_vendor_earnings,
            "unique_vendors": unique_vendors
        }
        
    except Exception as e:
        logger.error(f"Error getting platform revenue: {str(e)}")
        return {"error": str(e)}


async def get_pending_payouts() -> List[Dict]:
    """
    Get all pending payout requests.
    
    Returns:
        List of pending payout requests
    """
    try:
        pending_payouts = await PayoutRequest.filter(
            status=PayoutStatus.PENDING
        ).prefetch_related('vendor').order_by('-created_at').all()
        
        result = []
        for payout in pending_payouts:
            result.append({
                "id": payout.id,
                "vendor_id": payout.vendor.id,
                "vendor_name": payout.vendor.name,
                "vendor_telegram_id": payout.vendor.telegram_id,
                "amount": payout.amount,
                "currency": payout.currency,
                "period": f"{payout.period_year}-{payout.period_month:02d}",
                "created_at": payout.created_at.isoformat(),
                "status": payout.status
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting pending payouts: {str(e)}")
        return []


async def initialize_commission_structure():
    """
    Initialize default commission structure if none exists.
    """
    try:
        existing_commission = await Commission.all().first()
        if not existing_commission:
            current_time = get_current_almaty_time()
            await Commission.create(
                commission_rate=Decimal('0.15'),  # 15% default
                effective_from=current_time,
                description="Default platform commission rate"
            )
            logger.info("Initialized default commission structure (15%)")
        
    except Exception as e:
        logger.error(f"Error initializing commission structure: {str(e)}") 