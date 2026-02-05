# Chat API & WebSocket Guide

This document is for Flutter and Frontend teams. It explains how to start a chat, get room IDs, fetch history, and connect to WebSocket.

**Roles**
1. Visitor: the person who scans the QR and opens the website.
2. Owner: the car owner using the mobile app.

**Base URL**
Use your domain, for example:
```
https://carinfopro.uz
```

**Auth**
1. Owner uses JWT in `Authorization: Bearer <JWT_ACCESS>`.
2. Visitor uses `visitor_token` returned by `/api/chat/start/`.

**REST Endpoints**
| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/api/chat/start/` | Public | Create a room for a visitor. Returns `room_id` and `visitor_token`. |
| GET | `/api/chat/rooms/` | Owner (JWT) | List rooms for the owner. Used by the app to get new room IDs. |
| GET | `/api/chat/rooms/<room_id>/messages/` | Owner (JWT) or Visitor token | Get message history for a room. |

**1) Start Chat (Visitor)**
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

**2) Get Room IDs (Owner App)**
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

**3) Get Message History**
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
Base:
```
ws://YOUR_DOMAIN/ws/chat/<room_id>/
```
If HTTPS, use:
```
wss://YOUR_DOMAIN/ws/chat/<room_id>/
```

Visitor connection:
```
wss://YOUR_DOMAIN/ws/chat/<room_id>/?visitor=<visitor_token>
```

Owner connection:
```
wss://YOUR_DOMAIN/ws/chat/<room_id>/?token=<JWT_ACCESS>
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
