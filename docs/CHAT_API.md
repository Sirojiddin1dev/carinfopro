# CarInfo API & WebSocket Guide

This document is for Flutter and Frontend teams. It covers REST APIs and real-time chat over WebSocket.

**Base URLs**
REST base:
```
https://carinfopro.uz/back
```
WebSocket base:
```
wss://carinfopro.uz/ws/chat/<room_id>/
```
If your reverse proxy keeps the `/back` prefix for WebSocket too, use:
```
wss://carinfopro.uz/back/ws/chat/<room_id>/
```

**Auth**
1. Owner uses JWT in `Authorization: Bearer <JWT_ACCESS>`.
2. Visitor uses `visitor_token` returned by `/api/chat/start/`.

**Time Format**
All timestamps are ISO 8601 strings.

**User & Auth REST Endpoints**
| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/api/user/register/` | Public | Register user after QR scan. |
| POST | `/api/login/` | Public | Login with phone and password. |
| POST | `/api/token/refresh/` | Public | Refresh JWT access token. |
| GET | `/api/profile/` | Owner (JWT) | Get current user profile. |
| PUT | `/api/profile/` | Owner (JWT) | Update current user profile (partial allowed). |
| PATCH | `/api/profile/` | Owner (JWT) | Partial update current user profile. |
| GET | `/api/users/` | Public | List public users. |
| GET | `/user/<user_id>/` | Public | Get public user profile by UUID. |
| GET | `/api/docs/` | Public | Swagger UI. |
| GET | `/api/redoc/` | Public | Redoc UI. |
| GET | `/api/schema/` | Public | OpenAPI schema. |

**Register After QR Scan**
Request:
```
POST /api/user/register/
Content-Type: application/json

{
  "user_id": "<USER_UUID>",
  "phone_number": "+998901234567",
  "password": "secret123",
  "full_name": "Optional",
  "phone_number_2": "Optional",
  "car_model": "Optional",
  "car_plate_number": "Optional",
  "instagram": "Optional",
  "telegram": "Optional",
  "whatsapp": "Optional",
  "is_profile_public": true
}
```
If this user was already registered, the API returns:
```
{
  "user_id": ["User already registered. Please login."]
}
```

**Login**
Request:
```
POST /api/login/
Content-Type: application/json

{
  "phone_number": "+998901234567",
  "password": "secret123"
}
```
Response:
```
{
  "tokens": {
    "refresh": "jwt_refresh",
    "access": "jwt_access"
  },
  "user": { ... }
}
```

**Profile (Owner)**
Use `Authorization: Bearer <JWT_ACCESS>`.

**Public Profile**
If user profile is hidden (`is_profile_public=false`), this returns 404.

**Chat REST Endpoints**
| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/api/chat/start/` | Public | Create a room for a visitor. Returns `room_id` and `visitor_token`. |
| GET | `/api/chat/rooms/` | Owner (JWT) | List rooms for the owner. Used by the app to get new room IDs. |
| GET | `/api/chat/rooms/<room_id>/messages/` | Owner (JWT) or Visitor token | Get message history for a room. |

**Start Chat (Visitor)**
Request:
```
POST /api/chat/start/
Content-Type: application/json

{
  "user_id": "<OWNER_UUID>",
  "visitor_name": "Optional"
}
```
Response:
```
{
  "room_id": "uuid",
  "visitor_token": "uuid",
  "ws_path": "/ws/chat/<room_id>/"
}
```

**Get Room IDs (Owner App)**
The owner does not press Start. The visitor creates a room on the site.
The owner app should poll:
```
GET /api/chat/rooms/
Authorization: Bearer <JWT_ACCESS>
```
Response:
```
[
  {
    "id": "room_uuid",
    "owner_id": "owner_uuid",
    "visitor_name": "",
    "is_active": true,
    "created_at": "2026-02-05T11:00:00Z",
    "updated_at": "2026-02-05T11:05:00Z"
  }
]
```
Polling suggestion: every 3 to 5 seconds, or on app foreground.

**Get Message History**
Owner:
```
GET /api/chat/rooms/<room_id>/messages/
Authorization: Bearer <JWT_ACCESS>
```
Visitor:
```
GET /api/chat/rooms/<room_id>/messages/?visitor=<visitor_token>
```
Response:
```
[
  {
    "id": "msg_uuid",
    "room_id": "room_uuid",
    "sender_type": "visitor",
    "content": "Salom",
    "created_at": "2026-02-05T11:06:00Z"
  }
]
```

**WebSocket**
Visitor connection:
```
wss://carinfopro.uz/ws/chat/<room_id>/?visitor=<visitor_token>
```
Owner connection:
```
wss://carinfopro.uz/ws/chat/<room_id>/?token=<JWT_ACCESS>
```

**Send a Message**
Client sends:
```
{"message":"Salom"}
```

Server broadcasts:
```
{
  "id": "msg_uuid",
  "room_id": "room_uuid",
  "sender_type": "visitor",
  "message": "Salom",
  "created_at": "2026-02-05T11:06:00Z"
}
```

**Notes**
1. `visitor_token` is sensitive. Treat it like a session token.
2. WebSocket requires ASGI server in production.
3. If Redis is configured, WebSocket works across multiple processes.
