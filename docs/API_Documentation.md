# API Documentation

## 📋 Table of Contents

1. [Authentication Endpoints](#authentication-endpoints)
2. [Event Management](#event-management)
3. [Ticket System](#ticket-system)
4. [Payment Integration](#payment-integration)
5. [Social Features](#social-features)
6. [Admin Endpoints](#admin-endpoints)
7. [Response Codes](#response-codes)
8. [Rate Limiting](#rate-limiting)

## 🔐 Authentication Endpoints

### Register User
```http
POST /auth/register
Content-Type: application/json
```

**Request Body:**
```json
{
  "name": "John Doe",
  "phone": "+919876543210",
  "email": "john@example.com",
  "password": "securepassword123"
}
```

**Response:**
```json
{
  "msg": "User registered successfully",
  "user": {
    "id": "u_abc123def4",
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "+919876543210",
    "createdAt": "2025-01-04T16:08:51+05:30"
  },
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer"
}
```

### Login User
```http
POST /auth/login
Content-Type: application/json
```

**Request Body:**
```json
{
  "phone": "+919876543210",
  "password": "securepassword123"
}
```

**Response:**
```json
{
  "msg": "login_successful",
  "user": {
    "id": "u_abc123def4",
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "+919876543210",
    "bio": "Fitness enthusiast",
    "strava_link": "https://strava.com/athletes/123456",
    "instagram_id": "john_fitness",
    "picture": "/uploads/profiles/u_abc123def4_pic.jpg",
    "createdAt": "2025-01-04T16:08:51+05:30"
  },
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer"
}
```

### Google OAuth Login
```http
GET /auth/google_login
```

**Flow:**
1. Redirects to Google OAuth consent screen
2. User authorizes application
3. Callback to `/auth/google_login/callback`
4. Returns user data and access token

### Update User Profile
```http
PUT /auth/user/{user_id}
Content-Type: multipart/form-data
```

**Form Data:**
- `name`: User's full name
- `phone`: Phone number
- `email`: Email address
- `bio`: User biography
- `strava_link`: Strava profile URL
- `instagram_id`: Instagram handle
- `picture`: Profile image file

**Headers:**
```
X-User-ID: u_abc123def4
```

## 🎫 Event Management

### Create Event
```http
POST /events/create
Content-Type: application/json
Authorization: Bearer <token>
```

**Request Body:**
```json
{
  "title": "Morning Yoga Session",
  "description": "Relaxing yoga session for all levels",
  "event_type": "yoga",
  "start_time": "2025-01-15T06:00:00+05:30",
  "end_time": "2025-01-15T07:30:00+05:30",
  "location": "Central Park, Mumbai",
  "latitude": 19.0760,
  "longitude": 72.8777,
  "max_participants": 50,
  "price_inr": 500,
  "difficulty_level": "beginner",
  "requirements": "Yoga mat, water bottle",
  "tags": ["yoga", "morning", "wellness"]
}
```

### Get All Events
```http
GET /events/all
```

**Query Parameters:**
- `page`: Page number (default: 1)
- `limit`: Items per page (default: 10)
- `event_type`: Filter by event type
- `location`: Location-based search
- `start_date`: Filter events from date
- `end_date`: Filter events until date

**Response:**
```json
{
  "events": [
    {
      "id": "e_xyz789ghi0",
      "title": "Morning Yoga Session",
      "description": "Relaxing yoga session for all levels",
      "organizer_id": "u_abc123def4",
      "start_time": "2025-01-15T06:00:00+05:30",
      "end_time": "2025-01-15T07:30:00+05:30",
      "location": "Central Park, Mumbai",
      "max_participants": 50,
      "current_participants": 23,
      "price_inr": 500,
      "registration_link": "https://app.com/events/e_xyz789ghi0"
    }
  ],
  "total": 156,
  "page": 1,
  "total_pages": 16
}
```

### Get Event Details
```http
GET /events/{event_id}
```

**Response:**
```json
{
  "event": {
    "id": "e_xyz789ghi0",
    "title": "Morning Yoga Session",
    "description": "Relaxing yoga session for all levels",
    "organizer": {
      "id": "u_abc123def4",
      "name": "John Doe",
      "picture": "/uploads/profiles/u_abc123def4_pic.jpg"
    },
    "start_time": "2025-01-15T06:00:00+05:30",
    "end_time": "2025-01-15T07:30:00+05:30",
    "location": "Central Park, Mumbai",
    "coordinates": [19.0760, 72.8777],
    "max_participants": 50,
    "current_participants": 23,
    "price_inr": 500,
    "difficulty_level": "beginner",
    "requirements": "Yoga mat, water bottle",
    "tags": ["yoga", "morning", "wellness"],
    "images": ["/uploads/events/e_xyz789ghi0_1.jpg"],
    "registration_deadline": "2025-01-14T23:59:59+05:30",
    "created_at": "2025-01-01T10:00:00+05:30"
  }
}
```

### Update Event
```http
PUT /events/{event_id}
Content-Type: application/json
Authorization: Bearer <token>
```

**Request Body:** Same as create event (all fields optional)

### Delete Event
```http
DELETE /events/{event_id}
Authorization: Bearer <token>
```

## 🎫 Ticket System

### Book Event Ticket
```http
POST /tickets/book
Content-Type: application/json
Authorization: Bearer <token>
```

**Request Body:**
```json
{
  "event_id": "e_xyz789ghi0",
  "participant_details": {
    "name": "Jane Smith",
    "phone": "+919876543211",
    "email": "jane@example.com",
    "emergency_contact": "+919876543212"
  }
}
```

**Response:**
```json
{
  "ticket": {
    "id": "t_ticket123",
    "event_id": "e_xyz789ghi0",
    "user_id": "u_user456",
    "participant_name": "Jane Smith",
    "qr_code": "qr_abc123def456",
    "status": "confirmed",
    "booking_time": "2025-01-04T16:08:51+05:30",
    "payment_id": "pay_payment789"
  },
  "payment_required": true,
  "payment_url": "https://razorpay.com/payment_link/pl_xyz789"
}
```

### Get User Tickets
```http
GET /tickets/my-tickets
Authorization: Bearer <token>
```

**Response:**
```json
{
  "tickets": [
    {
      "id": "t_ticket123",
      "event": {
        "id": "e_xyz789ghi0",
        "title": "Morning Yoga Session",
        "start_time": "2025-01-15T06:00:00+05:30",
        "location": "Central Park, Mumbai"
      },
      "status": "confirmed",
      "qr_code": "qr_abc123def456",
      "booking_time": "2025-01-04T16:08:51+05:30"
    }
  ]
}
```

### Generate QR Code
```http
POST /tickets/{ticket_id}/generate-qr
Authorization: Bearer <token>
```

**Response:**
```json
{
  "qr_code": "qr_abc123def456",
  "qr_image_url": "/uploads/qr/qr_abc123def456.png",
  "expires_at": "2025-01-15T07:30:00+05:30"
}
```

### Validate QR Code (Event Check-in)
```http
POST /tickets/validate-qr
Content-Type: application/json
```

**Request Body:**
```json
{
  "qr_code": "qr_abc123def456",
  "event_id": "e_xyz789ghi0"
}
```

**Response:**
```json
{
  "valid": true,
  "ticket": {
    "id": "t_ticket123",
    "participant_name": "Jane Smith",
    "event_title": "Morning Yoga Session"
  },
  "checked_in_at": "2025-01-15T06:15:00+05:30"
}
```

## 💳 Payment Integration

### Create Payment Order
```http
POST /payments/create-order
Content-Type: application/json
Authorization: Bearer <token>
```

**Request Body:**
```json
{
  "amount": 500,
  "currency": "INR",
  "ticket_id": "t_ticket123",
  "description": "Morning Yoga Session - Entry Fee"
}
```

**Response:**
```json
{
  "order_id": "order_xyz789",
  "amount": 500,
  "currency": "INR",
  "razorpay_order_id": "order_ABC123XYZ",
  "payment_url": "https://checkout.razorpay.com/v1/checkout/order_ABC123XYZ"
}
```

### Payment Webhook
```http
POST /payments/webhook
```

**Webhook Body (from Razorpay):**
```json
{
  "event": "payment.authorized",
  "payload": {
    "payment": {
      "entity": {
        "id": "pay_ABC123XYZ",
        "status": "authorized",
        "amount": 500,
        "currency": "INR",
        "order_id": "order_xyz789"
      }
    }
  }
}
```

### Get Payment Status
```http
GET /payments/status/{payment_id}
```

**Response:**
```json
{
  "payment_id": "pay_ABC123XYZ",
  "status": "paid",
  "amount": 500,
  "currency": "INR",
  "method": "card",
  "captured": true,
  "description": "Morning Yoga Session - Entry Fee",
  "created_at": "2025-01-04T16:08:51+05:30"
}
```

## 👥 Social Features

### Follow User
```http
POST /social/follow/{user_id}
Authorization: Bearer <token>
```

**Response:**
```json
{
  "message": "Successfully followed user",
  "following": true
}
```

### Unfollow User
```http
DELETE /social/follow/{user_id}
Authorization: Bearer <token>
```

### Get User Followers
```http
GET /social/followers/{user_id}
```

**Response:**
```json
{
  "followers": [
    {
      "id": "u_follower123",
      "name": "Alice Johnson",
      "picture": "/uploads/profiles/u_follower123_pic.jpg",
      "followed_at": "2025-01-01T10:00:00+05:30"
    }
  ],
  "total": 42
}
```

### Get User Following
```http
GET /social/following/{user_id}
```

### Update Privacy Settings
```http
PUT /social/privacy
Content-Type: application/json
Authorization: Bearer <token>
```

**Request Body:**
```json
{
  "is_private": true,
  "allow_messages_from": "followers", // "everyone" | "followers" | "none"
  "show_events_to": "everyone" // "everyone" | "followers" | "none"
}
```

## 🔧 Admin Endpoints

### Get All Users
```http
GET /auth/users
Authorization: Bearer <admin_token>
```

### System Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "database": {
    "type": "PostgreSQL",
    "connection_test": "passed",
    "users_count": 1250
  },
  "file_system": "accessible",
  "memory": {
    "total": 8589934592,
    "available": 4294967296,
    "percent": 50.0
  },
  "cache": {
    "healthy": true
  },
  "timestamp": "2025-01-04T16:08:51+05:30"
}
```

### Cache Statistics
```http
GET /cache-stats
```

### Clear Cache
```http
POST /cache-clear
Authorization: Bearer <admin_token>
```

## 📊 Response Codes

| Code | Description |
|------|-------------|
| `200` | Success |
| `201` | Created |
| `400` | Bad Request |
| `401` | Unauthorized |
| `403` | Forbidden |
| `404` | Not Found |
| `409` | Conflict |
| `422` | Unprocessable Entity |
| `429` | Too Many Requests |
| `500` | Internal Server Error |

## 🚦 Rate Limiting

### Default Limits

| Endpoint Pattern | Limit | Window |
|------------------|-------|--------|
| `POST /auth/register` | 5 requests | 15 minutes |
| `POST /auth/login` | 10 requests | 15 minutes |
| `POST /auth/google_login` | 20 requests | 15 minutes |
| `GET /events/all` | 100 requests | 1 minute |
| `POST /tickets/book` | 30 requests | 1 minute |
| `POST /payments/create-order` | 50 requests | 1 minute |

### Rate Limit Headers

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1640995200
```

### Rate Limit Exceeded Response

```json
{
  "error": "Rate limit exceeded",
  "detail": "Too many requests",
  "retry_after": 300,
  "status_code": 429
}
```

---

## 🔒 Authentication

All protected endpoints require JWT token in header:
```
Authorization: Bearer <your_jwt_token>
```

Or user ID in header for certain operations:
```
X-User-ID: u_abc123def4
```

## 📝 Notes

- All timestamps are in IST (UTC+5:30)
- File uploads support: JPG, PNG, JPEG (max 5MB)
- Phone numbers should include country code
- Email validation follows standard format
- QR codes expire at event end time
- Payments are processed in INR only

---

*Last Updated: January 2025*
*API Version: v2.0.0*
