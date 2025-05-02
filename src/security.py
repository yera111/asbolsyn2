import time
import logging
import asyncio
from collections import defaultdict
from aiogram import types
from aiogram.types import Message
import re
from functools import wraps

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Rate limiting configuration
class RateLimiter:
    def __init__(self):
        # Store request timestamps for each user
        self.user_requests = defaultdict(list)
        # Store command usage counts
        self.command_usage = defaultdict(lambda: defaultdict(int))
        # Track potential spam/attack patterns
        self.suspicious_activity = defaultdict(int)
        # Banned users (temporarily or permanently)
        self.banned_users = set()
        # IP address tracking (for webhook mode)
        self.ip_requests = defaultdict(list)
        # Configure cleanup task
        self.cleanup_interval = 3600  # 1 hour
        
    async def start_cleanup_task(self):
        """Start periodic cleanup of old rate limit data"""
        while True:
            await asyncio.sleep(self.cleanup_interval)
            self._cleanup_old_data()
            
    def _cleanup_old_data(self):
        """Remove old request data to prevent memory buildup"""
        current_time = time.time()
        # Keep only last hour of data
        for user_id in list(self.user_requests.keys()):
            self.user_requests[user_id] = [
                timestamp for timestamp in self.user_requests[user_id]
                if current_time - timestamp < 3600
            ]
            if not self.user_requests[user_id]:
                del self.user_requests[user_id]
                
        # Reset command usage counts that are old
        for user_id in list(self.command_usage.keys()):
            if current_time - self.command_usage[user_id].get('last_reset', 0) > 86400:  # 24 hours
                del self.command_usage[user_id]
                
        # Reset IP tracking data
        for ip in list(self.ip_requests.keys()):
            self.ip_requests[ip] = [
                timestamp for timestamp in self.ip_requests[ip]
                if current_time - timestamp < 3600
            ]
            if not self.ip_requests[ip]:
                del self.ip_requests[ip]
                
        # Unban temporary banned users
        # (This would need to track ban expiry times in a real implementation)
        
        logger.info(f"Cleaned up rate limiting data. Tracking {len(self.user_requests)} users")
        
    def is_rate_limited(self, user_id, limit=5, period=60, request_type="general"):
        """
        Check if a user is exceeding rate limits
        
        Args:
            user_id: The Telegram user ID
            limit: Maximum number of requests allowed in the period
            period: Time period in seconds
            request_type: Type of request (for different limits)
            
        Returns:
            bool: True if user should be rate limited, False otherwise
        """
        if user_id in self.banned_users:
            logger.warning(f"Banned user {user_id} attempted to use the bot")
            return True
            
        current_time = time.time()
        
        # Add the current request timestamp
        self.user_requests[user_id].append(current_time)
        
        # Count recent requests within the period
        recent_requests = sum(
            1 for timestamp in self.user_requests[user_id]
            if current_time - timestamp < period
        )
        
        # Apply rate limiting if too many requests
        if recent_requests > limit:
            # Track suspicious activity
            self.suspicious_activity[user_id] += 1
            
            # Ban user temporarily if consistently abusing
            if self.suspicious_activity[user_id] > 5:
                logger.warning(f"User {user_id} temporarily banned for excessive requests")
                self.banned_users.add(user_id)
                
            logger.warning(f"Rate limit exceeded for user {user_id}: {recent_requests} requests in {period}s")
            return True
            
        return False
        
    def track_command(self, user_id, command):
        """
        Track command usage for a user
        
        Args:
            user_id: The Telegram user ID
            command: The command being used
        """
        current_time = time.time()
        
        # Update last reset time if needed
        if 'last_reset' not in self.command_usage[user_id] or \
           current_time - self.command_usage[user_id]['last_reset'] > 86400:  # 24 hours
            self.command_usage[user_id] = {'last_reset': current_time}
            
        # Increment command count
        self.command_usage[user_id][command] = self.command_usage[user_id].get(command, 0) + 1
        
        # Check for suspicious patterns
        if self.command_usage[user_id][command] > 50:  # Unusually high command usage
            self.suspicious_activity[user_id] += 1
            logger.warning(f"Suspicious command usage pattern for user {user_id}: {command} used {self.command_usage[user_id][command]} times")
            
    def track_ip(self, ip_address):
        """
        Track requests from a specific IP address (for webhook mode)
        
        Args:
            ip_address: The IP address making the request
            
        Returns:
            bool: True if IP should be blocked, False otherwise
        """
        current_time = time.time()
        
        # Add the current request timestamp
        self.ip_requests[ip_address].append(current_time)
        
        # Count recent requests within a short period (10 seconds)
        recent_requests = sum(
            1 for timestamp in self.ip_requests[ip_address]
            if current_time - timestamp < 10
        )
        
        # Apply IP blocking if too many requests in a short time
        if recent_requests > 30:  # More than 30 requests in 10 seconds
            logger.warning(f"Possible DDOS from IP {ip_address}: {recent_requests} requests in 10s")
            return True
            
        return False

# Create a global rate limiter instance
rate_limiter = RateLimiter()

# Spam detection
def contains_spam(text):
    """
    Check if message contains potential spam patterns
    
    Args:
        text: The message text to check
        
    Returns:
        bool: True if message appears to be spam, False otherwise
    """
    if not text:
        return False
        
    # Check for excessive URLs
    url_pattern = re.compile(r'https?://\S+')
    urls = url_pattern.findall(text)
    if len(urls) > 3:
        return True
        
    # Check for message length (spam is often very long)
    if len(text) > 1000:
        return True
        
    # Check for repetitive patterns
    repetition_pattern = re.compile(r'(.+?)\1{4,}')
    if repetition_pattern.search(text):
        return True
        
    return False

# Middleware to apply rate limiting
def rate_limit(limit=5, period=60, key=None):
    """
    Decorator to apply rate limiting to handler functions
    
    Args:
        limit: Maximum number of requests allowed in the period
        period: Time period in seconds
        key: Optional key to use different rate limits for different handlers
    """
    def decorator(handler):
        @wraps(handler)
        async def wrapper(message: Message, *args, **kwargs):
            user_id = message.from_user.id
            request_type = key or handler.__name__
            
            # Track command usage if it's a command
            if message.content_type == types.ContentType.TEXT and message.text and message.text.startswith("/"):
                command = message.text.split()[0]
                rate_limiter.track_command(user_id, command)
            
            # Check for spam in text messages
            if message.content_type == types.ContentType.TEXT and contains_spam(message.text):
                logger.warning(f"Spam message detected from user {user_id}")
                await message.answer("Ваше сообщение было заблокировано как возможный спам.")
                return
            
            # Check rate limits
            if rate_limiter.is_rate_limited(user_id, limit, period, request_type):
                await message.answer("Вы слишком часто используете этот бот. Пожалуйста, подождите немного перед повторной попыткой.")
                return
            
            # If not rate limited, proceed with the handler
            return await handler(message, *args, **kwargs)
        return wrapper
    return decorator

# Webhook security middleware
async def webhook_security_middleware(request, handler):
    """
    Middleware for webhook security
    
    Args:
        request: The aiohttp request
        handler: The handler function
    """
    # Get client IP
    ip = request.remote
    
    # Check if this IP is sending too many requests
    if rate_limiter.track_ip(ip):
        logger.warning(f"Blocked potential DDOS attack from IP: {ip}")
        return
    
    # Check for suspicious headers or payload size
    if request.content_length and request.content_length > 1024 * 1024:  # > 1MB
        logger.warning(f"Oversized webhook payload from IP: {ip}")
        return
    
    # If no security issues, proceed with the handler
    return await handler(request)

# Start the periodic cleanup task
async def start_security_tasks():
    """Start security-related background tasks"""
    asyncio.create_task(rate_limiter.start_cleanup_task()) 