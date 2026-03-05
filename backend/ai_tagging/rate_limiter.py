"""Rate limiter for Gemini API calls."""

import asyncio
import logging
from datetime import datetime, timedelta
from collections import deque
from .config import REQUESTS_PER_MINUTE

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token bucket rate limiter for Gemini API."""
    
    def __init__(self, requests_per_minute: int = REQUESTS_PER_MINUTE):
        """Initialize rate limiter."""
        self.requests_per_minute = requests_per_minute
        self.request_times: deque = deque(maxlen=requests_per_minute)
        self.lock = asyncio.Lock()
    
    async def check_limit(self) -> None:
        """
        Check if we can make a request. Wait if necessary.
        Raises TimeoutError if waiting exceeds reasonable limits.
        """
        async with self.lock:
            now = datetime.utcnow()
            
            # Remove old requests outside the current minute
            while self.request_times and self.request_times[0] < now - timedelta(minutes=1):
                self.request_times.popleft()
            
            # If at limit, wait
            if len(self.request_times) >= self.requests_per_minute:
                # Wait until the oldest request is outside the window
                oldest = self.request_times[0]
                wait_time = (oldest + timedelta(minutes=1) - now).total_seconds()
                
                if wait_time > 0:
                    logger.info(f"Rate limit reached. Waiting {wait_time:.2f} seconds...")
                    await asyncio.sleep(wait_time)
                    # Recursively check again after waiting
                    await self.check_limit()
                    return
            
            # Record this request
            self.request_times.append(now)
            logger.debug(f"Request allowed. {len(self.request_times)}/{self.requests_per_minute} capacity used.")
