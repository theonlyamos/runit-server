import re
import secrets
import hashlib
import base64
import time
from collections import defaultdict
from threading import Lock
from typing import Dict, Tuple, Optional, List


class RateLimiter:
    """Thread-safe rate limiter for API endpoints."""
    
    _instance = None
    _lock = Lock()
    _requests = None
    _rate_lock = None
    
    def __init__(self):
        if RateLimiter._requests is None:
            RateLimiter._requests = defaultdict(list)
            RateLimiter._rate_lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def is_allowed(self, key: str, max_requests: int = 5, window_seconds: int = 60) -> Tuple[bool, int]:
        """
        Check if a request is allowed based on rate limits.
        
        :param key: Unique identifier (e.g., IP address)
        :param max_requests: Maximum requests allowed in window
        :param window_seconds: Time window in seconds
        
        :return: Tuple of (is_allowed, retry_after_seconds)
        """
        current_time = time.time()
        cutoff_time = current_time - window_seconds
        
        with RateLimiter._rate_lock:
            RateLimiter._requests[key] = [
                t for t in RateLimiter._requests[key] if t > cutoff_time
            ]
            
            if len(RateLimiter._requests[key]) >= max_requests:
                oldest = RateLimiter._requests[key][0]
                retry_after = int(oldest + window_seconds - current_time)
                return False, max(1, retry_after)
            
            RateLimiter._requests[key].append(current_time)
            return True, 0
    
    def clear(self, key = None):
        """Clear rate limit for a key or all keys."""
        with RateLimiter._rate_lock:
            if key:
                RateLimiter._requests.pop(key, None)
            else:
                RateLimiter._requests.clear()


rate_limiter = RateLimiter()


class Utils(object):

    @staticmethod
    def email_is_valid(email: str) -> bool:
        """
        Checks if the provided email is a valid
        email address
        
        :param email: Email Address
        
        :return: True if email is valid, False otherwise
        """
        
        email_address_matcher = re.compile(r'^[\w\.-]+@([\w-]+\.)+[\w]+$')
        return True if email_address_matcher.match(email) else False

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hashes a password using PBKDF2 with SHA512.
        
        :param password: The password from the login/register form
        
        :return: A hashed password string
        """
        try:
            from passlib.hash import pbkdf2_sha512
            return pbkdf2_sha512.hash(password)
        except ImportError:
            salt = secrets.token_bytes(16)
            key = hashlib.pbkdf2_hmac(
                'sha512',
                password.encode('utf-8'),
                salt,
                100000
            )
            return base64.b64encode(salt + key).decode('utf-8')

    @staticmethod
    def check_hashed_password(password: str, hashed_password: str) -> bool:
        """
        Checks that the password the user sent matches that of the database.
        
        :param password: password
        :param hashed_password: hashed password
        
        :return: True if passwords match, False otherwise
        """
        try:
            from passlib.hash import pbkdf2_sha512
            return pbkdf2_sha512.verify(password, hashed_password)
        except ImportError:
            decoded = base64.b64decode(hashed_password.encode('utf-8'))
            salt = decoded[:16]
            stored_key = decoded[16:]
            new_key = hashlib.pbkdf2_hmac(
                'sha512',
                password.encode('utf-8'),
                salt,
                100000
            )
            return secrets.compare_digest(stored_key, new_key)
    
    @staticmethod
    def is_strong_password(password: str) -> tuple[bool, str]:
        """
        Validates password strength.
        
        :param password: Password to validate
        
        :return: Tuple of (is_valid, message)
        """
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        if not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"
        if not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"
        if not re.search(r'\d', password):
            return False, "Password must contain at least one digit"
        return True, "Password is strong"