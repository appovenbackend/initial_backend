## 📋 **Complete Connection/Social API Documentation**

### **🔐 Authentication & Common Setup**

- **Base URL**: `/social`
- **Authentication**: `X-User-ID` header (simplified for testing; production uses JWT)
- **Database**: Uses `user_connections` table (formerly `user_follows`)

---

## **👤 User Profile Endpoints**

### **1. Get User Profile**

```http
GET /social/users/{user_id}
```

**What it does:**

- Retrieves detailed user profile information with privacy controls
- Shows different information based on viewer's relationship to the user

**How it works:**

1. **Authentication**: Extracts current user ID from `X-User-ID` header
2. **Data Retrieval**: Loads user data and connection records from database
3. **Privacy Check**: Uses `_can_view_profile()` to determine visibility
4. **Profile Building**: Calls `_build_profile_response()` with privacy filtering
5. **Relationship Status**: Includes connection status between viewer and target

**Request:**

```http
GET /social/users/user456
Headers: X-User-ID: user123
```

**Response:**

```json
{
  "id": "user456",
  "name": "John Doe",
  "picture": null,
  "bio": "Fitness enthusiast",
  "is_private": false,
  "connections_count": 5,
  "strava_link": "https://strava.com/athletes/123",
  "instagram_id": "@johndoe",
  "subscribed_events": ["event1", "event2"],
  "created_at": "2025-01-01T00:00:00",
  "is_connected": true,
  "connection_status": "accepted"
}
```

**Privacy Logic:**

- **Public Profile** (`is_private: false`): Full info visible to everyone
- **Private Profile** (`is_private: true`): Limited info to non-connections, full info to connections
- **Hidden Fields**: Phone and email are never shown (privacy decision)

---

### **2. Update Privacy Settings**

```http
PUT /social/users/{user_id}/privacy?is_private={bool}
```

**What it does:**

- Allows users to toggle their profile privacy setting
- Controls who can see their full profile information

**How it works:**

1. **Authorization**: Verifies current user owns the profile
2. **Validation**: Updates `is_private` field in user record
3. **Persistence**: Saves changes to database
4. **Response**: Returns new privacy status

**Request:**

```http
PUT /social/users/user123/privacy?is_private=true
Headers: X-User-ID: user123
```

**Response:**

```json
{
  "message": "Account set to private",
  "is_private": true
}
```

**Business Rules:**

- Users can only update their own privacy settings
- Changes take effect immediately for all profile views

---

## **🤝 Connection Management Endpoints**

### **3. Request Connection**

```http
POST /social/users/{user_id}/connect
```

**What it does:**

- Initiates a connection request between users
- Auto-accepts for public profiles, creates pending request for private profiles

**How it works:**

1. **Validation**: Checks if users aren't already connected or have pending requests
2. **Self-Connection Check**: Prevents users from connecting to themselves
3. **Privacy-Based Logic**:
   - **Public target**: Auto-accepts connection
   - **Private target**: Creates pending request
4. **Database Update**: Creates new record in `user_connections` table
5. **Response**: Returns connection status and message

**Request:**

```http
POST /social/users/user456/connect
Headers: X-User-ID: user123
```

**Response (Public Target):**

```json
{
  "success": true,
  "message": "Connected with John Doe",
  "status": "accepted"
}
```

**Response (Private Target):**

```json
{
  "success": true,
  "message": "Connection request sent to John Doe",
  "status": "pending"
}
```

**Database Record Created:**

```json
{
  "id": "conn_abc123",
  "follower_id": "user123", // Requester
  "following_id": "user456", // Target
  "status": "accepted", // or "pending"
  "created_at": "2025-01-01T00:00:00",
  "updated_at": "2025-01-01T00:00:00"
}
```

---

### **4. Remove Connection**

```http
DELETE /social/users/{user_id}/disconnect
```

**What it does:**

- Removes existing connection or pending request between users
- Works in both directions (follower/following)

**How it works:**

1. **Authentication**: Identifies current user
2. **Connection Lookup**: Finds connection record in either direction
3. **Validation**: Ensures connection exists
4. **Deletion**: Removes record from database
5. **Response**: Confirms disconnection

**Request:**

```http
DELETE /social/users/user456/disconnect
Headers: X-User-ID: user123
```

**Response:**

```json
{
  "message": "Connection removed"
}
```

---

## **📨 Connection Request Management**

### **5. Get Pending Requests**

```http
GET /social/connection-requests
```

**What it does:**

- Retrieves all pending connection requests where current user is the target
- Shows who wants to connect with them

**How it works:**

1. **Authentication**: Gets current user ID
2. **Query Database**: Finds all pending requests targeting current user
3. **Profile Building**: Builds profile responses for each requester
4. **Response**: Returns list of pending requests with requester details

**Request:**

```http
GET /social/connection-requests
Headers: X-User-ID: user123
```

**Response:**

```json
[
  {
    "id": "conn_abc123",
    "requester": {
      "id": "user456",
      "name": "John Doe",
      "picture": null,
      "bio": "Runner from Mumbai",
      "is_private": false,
      "connections_count": 2,
      "strava_link": null,
      "instagram_id": null,
      "subscribed_events": [],
      "created_at": "2025-01-01T00:00:00",
      "is_connected": false,
      "connection_status": null
    },
    "created_at": "2025-01-01T00:00:00"
  }
]
```

---

### **6. Accept Connection Request**

```http
POST /social/connection-requests/{request_id}/accept
```

**What it does:**

- Accepts a pending connection request
- Changes request status from "pending" to "accepted"

**How it works:**

1. **Authorization**: Verifies current user is the request target
2. **Request Lookup**: Finds specific request by ID
3. **Status Validation**: Ensures request is still pending
4. **Status Update**: Changes status to "accepted"
5. **Timestamp Update**: Sets updated_at timestamp
6. **Persistence**: Saves changes to database

**Request:**

```http
POST /social/connection-requests/conn_abc123/accept
Headers: X-User-ID: user123
```

**Response:**

```json
{
  "message": "Connection request accepted"
}
```

---

### **7. Decline Connection Request**

```http
POST /social/connection-requests/{request_id}/decline
```

**What it does:**

- Declines a pending connection request
- Removes the request entirely from database

**How it works:**

1. **Authorization**: Verifies current user is the request target
2. **Request Lookup**: Finds specific request by ID
3. **Validation**: Ensures request exists and user is authorized
4. **Deletion**: Removes request record from database
5. **Response**: Confirms request declined

**Request:**

```http
POST /social/connection-requests/conn_abc123/decline
Headers: X-User-ID: user123
```

**Response:**

```json
{
  "message": "Connection request declined"
}
```

---

## **👥 Network & Discovery Endpoints**

### **8. Get User Connections**

```http
GET /social/users/{user_id}/connections
```

**What it does:**

- Retrieves list of users connected to specified user
- Shows mutual connections (accepted in either direction)

**How it works:**

1. **Authentication**: Gets current user ID
2. **Privacy Check**: Verifies viewer can see target's connections
3. **Connection Query**: Finds all accepted connections in both directions
4. **Profile Building**: Builds profile responses for each connection
5. **Response**: Returns connections list with count

**Request:**

```http
GET /social/users/user456/connections
Headers: X-User-ID: user123
```

**Response:**

```json
{
  "connections": [
    {
      "id": "user789",
      "name": "Jane Smith",
      "picture": null,
      "bio": "Marathon runner",
      "is_private": false,
      "connections_count": 3,
      "strava_link": "https://strava.com/athletes/456",
      "instagram_id": "@janesmith",
      "subscribed_events": ["event1"],
      "created_at": "2025-01-01T00:00:00",
      "is_connected": true,
      "connection_status": "accepted"
    }
  ],
  "count": 1
}
```

**Privacy Rules:**

- **Public Profiles**: Anyone can view connections
- **Private Profiles**: Only connections can view connections list

---

### **9. Get My Connections (Alias)**

```http
GET /social/users/{user_id}/connections/mine
```

- **Identical functionality** to `/connections` endpoint
- **Same response format** and behavior
- **Maintained for API compatibility**

---

## **🎯 Activity & Social Features**

### **10. Get Activity Feed**

```http
GET /social/feed?limit={number}
```

**What it does:**

- Shows events attended by connected users
- Provides social activity stream from user's network

**How it works:**

1. **Authentication**: Gets current user ID
2. **Network Discovery**: Finds all users connected to current user
3. **Event Matching**: Gets events where connected users have tickets
4. **Activity Compilation**: Combines event and user attendance data
5. **Sorting**: Orders by most recent attendance
6. **Pagination**: Limits results based on `limit` parameter

**Request:**

```http
GET /social/feed?limit=20
Headers: X-User-ID: user123
```

**Response:**

```json
{
  "activities": [
    {
      "event": {
        "id": "event123",
        "title": "Morning Yoga Session",
        "description": "Start your day with yoga",
        "city": "Mumbai",
        "venue": "Juhu Beach",
        "startAt": "2025-01-01T06:00:00",
        "endAt": "2025-01-01T07:00:00",
        "priceINR": 0,
        "bannerUrl": null,
        "isActive": true,
        "createdAt": "2025-01-01T00:00:00",
        "organizerName": "bhag",
        "organizerLogo": "https://example.com/default-logo.png",
        "coordinate_lat": "19.0760",
        "coordinate_long": "72.8777",
        "address_url": null
      },
      "user_id": "user456",
      "attended_at": "2025-01-01T06:30:00"
    }
  ],
  "total": 1
}
```

**Activity Logic:**

- Only shows events from **accepted connections**
- Sorts by most recent attendance first
- Includes full event details with attendance metadata

---

### **11. Search Users**

```http
GET /social/users/search?q={query}&limit={number}
```

**What it does:**

- Searches users by name with privacy-aware results
- Returns matching users with their profile information

**How it works:**

1. **Input Validation**: Ensures query is at least 2 characters
2. **Authentication**: Gets current user ID
3. **Search Execution**: Finds users matching query (case-insensitive)
4. **Exclusion**: Removes current user from results
5. **Profile Building**: Builds profile responses with privacy filtering
6. **Limiting**: Restricts results based on limit parameter

**Request:**

```http
GET /social/users/search?q=john&limit=10
Headers: X-User-ID: user123
```

**Response:**

```json
{
  "users": [
    {
      "id": "user456",
      "name": "John Doe",
      "picture": null,
      "bio": "Fitness enthusiast",
      "is_private": false,
      "connections_count": 5,
      "strava_link": null,
      "instagram_id": null,
      "subscribed_events": [],
      "created_at": "2025-01-01T00:00:00",
      "is_connected": false,
      "connection_status": null
    }
  ],
  "count": 1
}
```

**Search Features:**

- **Case-insensitive** matching
- **Partial name** matching
- **Privacy-aware** results
- **Self-exclusion** (doesn't show current user)

---

## **📢 Admin & Communication Endpoints**

### **12. Admin Notify All Users**

```http
POST /social/admin/notify/all
Content-Type: application/json
{
  "message": "Your message here"
}
```

**What it does:**

- Sends WhatsApp message to all users who have phone numbers
- Uses WhatsApp service for bulk messaging

**How it works:**

1. **User Query**: Gets all users with phone numbers
2. **Message Preparation**: Formats message for WhatsApp service
3. **Bulk Sending**: Calls WhatsApp service with phone list
4. **Response**: Returns delivery statistics

**Request Body:**

```json
{
  "message": "Hello everyone! New features are now available."
}
```

**Response:**

```json
{
  "sent": 15,
  "total": 20
}
```

---

### **13. Admin Notify Event Subscribers**

```http
POST /social/admin/notify/event/{event_id}
Content-Type: application/json
{
  "message": "Your message here"
}
```

**What it does:**

- Sends WhatsApp message to users subscribed to specific event
- Targets only users who have opted into event notifications

**How it works:**

1. **Subscriber Query**: Finds users with phone numbers subscribed to event
2. **Filtering**: Checks `subscribedEvents` array for event ID
3. **Message Sending**: Uses WhatsApp service for delivery
4. **Statistics**: Returns delivery count

**Request Body:**

```json
{
  "message": "Event update: Tomorrow's run is cancelled due to weather."
}
```

**Response:**

```json
{
  "sent": 8,
  "total": 12
}
```

---

## **🔒 Privacy & Security Features**

### **Privacy Controls:**

- **Profile Visibility**: Public vs private account settings
- **Connection-Based Access**: Different info for connections vs non-connections
- **Sensitive Data Protection**: Phone/email never exposed in API responses
- **Admin Override**: Admin endpoints for bulk communications

### **Security Measures:**

- **Authentication Required**: All endpoints need user identification
- **Authorization Checks**: Users can only modify their own data
- **Input Validation**: Prevents invalid requests and self-connections
- **Rate Limiting**: Built-in protection against abuse

---

## **📊 Data Flow Architecture**

```
User Request → FastAPI Router → Business Logic → Database Layer → Response
     ↓              ↓              ↓            ↓            ↓
1. Auth Check    2. Validation   3. Privacy    4. SQLAlchemy 5. JSON Response
                  & Processing    Filtering    Query
```

This comprehensive API provides a full social networking experience with robust privacy controls, connection management, activity feeds, and administrative capabilities. Each endpoint is designed with security, privacy, and usability in mind! 🚀
