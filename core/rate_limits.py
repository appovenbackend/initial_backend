"""
Rate limiting configuration for different endpoint categories
"""

from slowapi.util import get_remote_address

# Rate limit configurations by category
RATE_LIMITS = {
    # Authentication endpoints - strict limits to prevent brute force
    'auth': {
        'limit': "5/minute",
        'key_func': get_remote_address,
        'description': 'Authentication endpoints (login, register, password reset)'
    },

    # Payment endpoints - moderate limits for security
    'payment': {
        'limit': "10/minute",
        'key_func': get_remote_address,
        'description': 'Payment processing endpoints'
    },

    # User profile operations - moderate limits
    'profile': {
        'limit': "20/minute",
        'key_func': get_remote_address,
        'description': 'User profile operations (view, update, connect)'
    },

    # Social features - relaxed limits for better UX
    'social': {
        'limit': "30/minute",
        'key_func': get_remote_address,
        'description': 'Social features (search, feed, connections)'
    },

    # Admin operations - very strict limits
    'admin': {
        'limit': "5/minute",
        'key_func': get_remote_address,
        'description': 'Administrative operations'
    },

    # Public endpoints - moderate limits
    'public': {
        'limit': "60/minute",
        'key_func': get_remote_address,
        'description': 'Public endpoints (health, events list)'
    },

    # Critical security endpoints - very strict
    'security': {
        'limit': "3/minute",
        'key_func': get_remote_address,
        'description': 'Critical security endpoints'
    }
}

# Endpoint categorization for rate limiting
ENDPOINT_RATE_LIMITS = {
    # Authentication endpoints
    'POST:/auth/login': 'auth',
    'POST:/auth/register': 'auth',
    'POST:/auth/forgot-password': 'auth',
    'POST:/auth/reset-password': 'auth',
    'POST:/auth/verify-otp': 'auth',

    # Payment endpoints
    'POST:/payments/order': 'payment',
    'POST:/payments/verify': 'payment',
    'POST:/payments/webhook': 'payment',

    # User profile endpoints
    'GET:/users/{user_id}': 'profile',
    'PUT:/users/{user_id}': 'profile',
    'PUT:/users/{user_id}/privacy': 'profile',
    'POST:/users/{user_id}/connect': 'profile',
    'DELETE:/users/{user_id}/disconnect': 'profile',
    'GET:/users/{user_id}/connections': 'profile',

    # Social endpoints
    'GET:/social/users/{user_id}': 'social',
    'GET:/social/connection-requests': 'social',
    'POST:/social/connection-requests/{request_id}/accept': 'social',
    'POST:/social/connection-requests/{request_id}/decline': 'social',
    'GET:/social/connections': 'social',
    'GET:/social/feed': 'social',
    'GET:/social/users/search': 'social',

    # Event endpoints (public)
    'GET:/events': 'public',
    'GET:/events/{event_id}': 'public',
    'GET:/events/recent': 'public',

    # Ticket endpoints
    'POST:/register/free': 'profile',
    'GET:/tickets/{user_id}': 'profile',
    'GET:/tickets/ticket/{ticket_id}': 'profile',
    'POST:/validate': 'security',

    # Admin endpoints
    'POST:/social/admin/notify/all': 'admin',
    'POST:/social/admin/notify/event/{event_id}': 'admin',
    'POST:/cache-clear': 'admin',
    'GET:/cache-stats': 'admin',

    # Health and monitoring
    'GET:/health': 'public',
    'GET:/': 'public',
}

def get_rate_limit_config(endpoint: str, method: str) -> dict:
    """
    Get rate limiting configuration for a specific endpoint

    Args:
        endpoint: The endpoint path (e.g., '/users/123')
        method: HTTP method (e.g., 'GET', 'POST')

    Returns:
        Rate limiting configuration dictionary
    """
    # Create endpoint key
    endpoint_key = f"{method}:{endpoint}"

    # Find matching pattern
    for pattern, category in ENDPOINT_RATE_LIMITS.items():
        if _matches_endpoint_pattern(endpoint_key, pattern):
            return RATE_LIMITS[category]

    # Default to public rate limit
    return RATE_LIMITS['public']

def _matches_endpoint_pattern(endpoint_key: str, pattern: str) -> bool:
    """
    Check if an endpoint matches a pattern with wildcards

    Args:
        endpoint_key: The actual endpoint (e.g., 'GET:/users/123')
        pattern: Pattern with wildcards (e.g., 'GET:/users/{user_id}')

    Returns:
        True if endpoint matches pattern
    """
    # Simple pattern matching for now
    # In production, consider using a more sophisticated pattern matcher

    # Handle parameterized routes
    if '{' in pattern and '}' in pattern:
        # Extract the base pattern (e.g., 'GET:/users/' from 'GET:/users/{user_id}')
        base_pattern = pattern.split('{')[0]
        return endpoint_key.startswith(base_pattern)

    # Exact match
    return endpoint_key == pattern

# Progressive rate limiting for repeat offenders
PROGRESSIVE_LIMITS = {
    'violation_1': "5/minute",      # First violation
    'violation_2': "3/minute",      # Second violation
    'violation_3': "1/minute",      # Third violation
    'violation_4+': "30/hour"       # Persistent offenders
}

# Rate limit violation tracking
VIOLATION_TRACKING = {
    'window_minutes': 60,           # Track violations in 1-hour windows
    'max_violations': 10,           # Max violations before progressive limiting
    'cooldown_minutes': 30          # Cooldown period after progressive limiting
}
