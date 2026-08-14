import json
import logging
import websockets
from database import SessionLocal
from fastapi import APIRouter, WebSocket, Depends, Query
from models import User, ChatRoom, Message, ChatReadStatus, RecentChat
#print(User)
#print(User.__module__)
#print(User.__table__.columns.keys())

from datetime import datetime, timezone
from fastapi.responses import JSONResponse
from database import SessionLocal
from sqlalchemy.orm import Session
from urllib.parse import parse_qs
from services.room_service import get_or_create_private_room

router = APIRouter()

#connections = []

# Track connections with room info
# Global connections dict
connections = {}  # {websocket: {"username": ..., "room_id": ...}}

#websocket endpoint
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    query = parse_qs(websocket.url.query)
    username = query.get("username", ["Anonymous"])[0]
    receiver = query.get("receiver", [None])[0]

    logging.info(
        f"Accepted connection: username={username}, receiver={receiver}"
    )

    db = SessionLocal()

    try:
        user = db.query(User).filter(
            User.username == username
        ).first()

        if not user:
            await websocket.close()
            return


        # Decide room
        if receiver:
            chat_room = get_or_create_private_room(
                db,
                username,
                receiver
            )
        else:
            chat_room = db.query(ChatRoom).filter(
                ChatRoom.name == "Public"
            ).first()


        if not chat_room:
            logging.error("Chat room not found!")
            await websocket.close()
            return


        # Store room information
        room_id = chat_room.id
        room_type = chat_room.room_type

        # Remove old websocket of same user
        #for old_ws, info in list(connections.items()):

        #    if info["username"] == username:

        #        try:
        #            await old_ws.close()
        #        except:
        #            pass

        #        connections.pop(old_ws, None)

        # Register new connection
        connections[websocket] = {
            "username": username,
            "room_id": room_id,
            "receiver": receiver
        }

        print("CONNECTED USERS:", [
            info["username"]
            for info in connections.values()
        ])

        # Online presence
        await broadcast_presence({
            "type": "presence",
            "username": username,
            "online": True,
            "last_seen": None
        })


        # Send current online users
        initial_presence = []

        all_users = db.query(User).filter(
            User.username != username
        ).all()


        online_names = {
            info["username"]
            for info in connections.values()
        }


        for user in all_users:

            initial_presence.append({

                "username": user.username,

                "online": user.username in online_names,

                "last_seen": (
                    user.last_seen.isoformat()+"Z"
                    if user.last_seen
                    else None
                )

            })


        await websocket.send_text(json.dumps({
            "type": "presence_init",
            "users": initial_presence
        }))


        while True:

            data = await websocket.receive_text()
            msg = json.loads(data)


            if msg.get("type") == "public_seen":

                message_id = msg.get("message_id")

                with SessionLocal() as db:

                    message = db.query(Message).filter(
                        Message.id == message_id,
                        Message.room_id == room_id,
                        Message.sender_id != user.id
                    ).first()


                    if not message:
                        continue


                    sender_name = (
                        message.sender.username
                        if message.sender
                        else None
                    )


                    print(
                        "PUBLIC SEEN:",
                        message.id,
                        sender_name
                    )


                    message.public_seen = 1

                    db.commit()


                    if sender_name:
                        await notify_public_seen(
                            sender_name,
                            message.id
                        )


                continue

            # Handle read receipt from websocket
            if msg.get("type") == "mark_read":

                with SessionLocal() as db:
                    #room_id = connections[websocket]["room_id"]

                    reader_user = db.query(User).filter(
                        User.username == username
                    ).first()

                    if not reader_user:
                        continue

                    target_receiver = msg.get("receiver")


                    if target_receiver:

                        room = get_or_create_private_room(
                            db,
                            username,
                            target_receiver
                        )

                        room_id = room.id

                    else:
                        continue

                    #reader = username

                    last_message = (
                        db.query(Message)
                        .filter(Message.room_id == room_id)
                        .order_by(Message.id.desc())
                        .first()
                    )

                    if last_message:

                        # update ChatReadStatus
                        status = db.query(ChatReadStatus).filter(
                            ChatReadStatus.user_id == reader_user.id,
                            ChatReadStatus.room_id == room_id
                        ).first()


                        if not status:
                            status = ChatReadStatus(
                                user_id=reader_user.id,
                                room_id=room_id
                            )
                            db.add(status)


                        status.last_read_message_id = last_message.id


                        # mark received messages as read
                        db.query(Message).filter(
                            Message.room_id == room_id,
                            Message.sender_id != reader_user.id,
                            Message.id <= last_message.id
                        ).update(
                            {
                                Message.is_read:1
                            },
                            synchronize_session=False
                        )


                        db.commit()


                        # notify sender
                        if receiver:
                            await notify_seen(
                                sender=target_receiver,
                                reader=username,
                                room_id=room_id,
                                last_read_id=last_message.id
                            )


                    continue

            if msg.get("type") in ["typing", "stop_typing"]:

                print(username, msg.get("type"))

                if receiver:

                    await notify_typing(
                        sender=username,
                        receiver=receiver,
                        typing=(msg.get("type") == "typing")
                    )

                continue

            if "message" not in msg:
                continue

            with SessionLocal() as db:

                user = db.query(User).filter(
                    User.username == username
                ).first()


                if not user:
                    continue

                room_id = connections[websocket]["room_id"]
                new_message = Message(
                    room_id=room_id,
                    sender_id=user.id,
                    message=msg["message"],
                    sent_at=datetime.utcnow()
                )

                db.add(new_message)
                db.commit()
                db.refresh(new_message)


                # Create unread status for receiver
                if receiver:

                    receiver_user = db.query(User).filter(
                        User.username == receiver
                    ).first()

                    if receiver_user:

                        create_or_update_unread_status(
                            db,
                            receiver_user.id,
                            room_id,
                            new_message.id
                        )


                payload = {
                    "type": "message",
                    "id": new_message.id,
                    "room_type": room_type,
                    "sender": username,
                    "receiver": receiver,
                    "message": msg["message"],
                    "avatar_color": user.avatar_color,
                    "sent_at": (
                        new_message.sent_at.isoformat() + "Z"
                    ),
                    "is_read": new_message.is_read,
                    "public_seen": new_message.public_seen,
                }


                #  Send message to opened chat room only
                if room_type == "public":
                    await broadcast_to_room(room_id, payload)
                else:
                    await notify_private_users(
                        username,
                        receiver,
                        payload
                    )


                #  Update recent chat sidebar only for two concern users (not everyone)
                await broadcast_chat_update(
                    sender=username,
                    receiver=receiver,
                    message=msg["message"],
                    sent_at=new_message.sent_at.isoformat() + "Z",
                    avatar_color=user.avatar_color
                )


    except Exception as e:
        logging.warning(
            f"Connection closed for {username}: {e}"
        )


    finally:

        if websocket in connections:

            username = connections[websocket]["username"]

            print("REMOVING:", username)

            print("BEFORE REMOVE:", [
                info["username"]
                for info in connections.values()
            ])

            # Remove this websocket
            del connections[websocket]

            print("AFTER REMOVE:", [
                info["username"]
                for info in connections.values()
            ])


            # Check whether this user still has another
            # active websocket connection
            still_connected = any(
                info["username"] == username
                for info in connections.values()
            )


            if not still_connected:

                print(
                    f"{username} has no active connections -> OFFLINE"
                )

                # Save last seen time
                with SessionLocal() as db:

                    user = db.query(User).filter(
                        User.username == username
                    ).first()

                    if user:

                        user.last_seen = datetime.utcnow()

                        db.commit()


                # Tell other users that this user is offline
                await broadcast_presence({
                    "type": "presence",
                    "username": username,
                    "online": False,
                    "last_seen": datetime.utcnow().isoformat() + "Z"
                })

            else:

                print(
                    f"{username} still has an active connection -> STAY ONLINE"
                )

        db.close()
        

# --- Helper functions ---
async def broadcast_presence(payload):
    """Send presence updates safely to all connections."""
    for conn in list(connections.keys()):
        try:
            await conn.send_text(json.dumps(payload))
        except Exception as e:
            logging.warning(f"Skipping closed connection: {e}")
            connections.pop(conn, None)

async def broadcast_to_room(room_id, payload):
    """Send messages safely to all connections in a room."""
    for conn, info in list(connections.items()):
        if info["room_id"] == room_id:
            try:
                await conn.send_text(json.dumps(payload))
            except Exception as e:
                logging.warning(f"Skipping closed connection: {e}")
                connections.pop(conn, None)

# play sound
async def notify_private_users(sender, receiver, payload):
    """Notify sender and receiver no matter which room they are viewing."""

    for conn, info in list(connections.items()):

        if info["username"] in [sender, receiver]:

            try:
                await conn.send_text(json.dumps(payload))
            except Exception:
                connections.pop(conn, None)

# seen mark
async def notify_seen(sender, reader, room_id, last_read_id):

    for conn, info in list(connections.items()):

        if info["username"] == sender:

            try:
                await conn.send_text(json.dumps({
                    "type": "messages_seen",
                    "reader": reader,
                    "room_id": room_id,
                    "last_read_id": last_read_id
                }))

            except Exception:
                connections.pop(conn, None)

# public seen mark                
async def notify_public_seen(sender, message_id):

    print(
        "SEND PUBLIC SEEN TO:",
        sender,
        message_id
    )

    for conn, info in list(connections.items()):

        print(
            "CONNECTED:",
            info["username"]
        )

        if info["username"] == sender:

            try:
                await conn.send_text(json.dumps({
                    "type":"public_message_seen",
                    "message_id":message_id
                }))

            except Exception:
                connections.pop(conn, None)


# typing behavior
async def notify_typing(sender, receiver, typing):

    for conn, info in list(connections.items()):

        if info["username"] == receiver:

            try:

                await conn.send_text(json.dumps({
                    "type": "typing",
                    "username": sender,
                    "typing": typing
                }))

            except Exception:
                connections.pop(conn, None)


# for read/unread noti blue circle
def create_or_update_unread_status(
    db,
    user_id,
    room_id,
    message_id
):

    status = db.query(ChatReadStatus).filter(
        ChatReadStatus.user_id == user_id,
        ChatReadStatus.room_id == room_id
    ).first()


    if not status:

        status = ChatReadStatus(
            user_id=user_id,
            room_id=room_id,
            last_read_message_id=message_id-1
        )

        db.add(status)

    db.commit()


async def broadcast_chat_update(sender, receiver, message, sent_at, avatar_color=None):

    """Send recent-chat updates only to sender and receiver."""

    # Public chat doesn't have receiver
    if receiver is None:
        return

    db = SessionLocal()

    sender_user = db.query(User).filter(User.username == sender).first()
    receiver_user = db.query(User).filter(User.username == receiver).first()
    
    for conn, info in list(connections.items()):

        if info["username"] == sender:
            payload = {
                "type": "chat_update",
                "sender": sender,
                "receiver": receiver,
                "last_sender": "You",
                "message": message,
                "sent_at": sent_at,
                "avatar_color": receiver_user.avatar_color
            }

        elif info["username"] == receiver:
            payload = {
                "type": "chat_update",
                "sender": sender,
                "receiver": receiver,
                "last_sender": sender,
                "message": message,
                "sent_at": sent_at,
                "avatar_color": sender_user.avatar_color
            }

        else:
            continue

        try:
            await conn.send_text(json.dumps(payload))
        except Exception:
            connections.pop(conn, None)
    db.close()

# chat history API
@router.get("/messages")
def get_messages(room_id: int = Query(None),
                receiver: str = Query(None),
                username: str = Query(None)):
    with SessionLocal() as db:
        user = db.query(User).filter(User.username == username).first() # for validation

        if room_id:
            messages = db.query(Message).filter(
                Message.room_id == room_id
            ).order_by(Message.id).all()

        elif receiver and username:
            room = get_or_create_private_room(db, username, receiver)

            # get user's clear history point
            user = db.query(User).filter(
                User.username == username
            ).first()


            contact = db.query(User).filter(
                User.username == receiver
            ).first()

            recent = db.query(RecentChat).filter(
                RecentChat.owner_id == user.id,
                RecentChat.contact_id == contact.id
            ).first()

            cleared_id = (
                recent.cleared_message_id
                if recent
                else 0
            )

            messages = db.query(Message).filter(
                Message.room_id == room.id,
                Message.id > cleared_id
            ).order_by(Message.id).all()


        else:
            public_room = db.query(ChatRoom).filter(
                ChatRoom.name == "Public"
            ).first()
            messages = db.query(Message).filter(
                Message.room_id == public_room.id
            ).order_by(Message.id).all()

        return [
            {
                "id": msg.id,
                "sender": msg.sender.username if msg.sender else "Deleted User",
                "deleted_user": msg.sender is None,
                "avatar_color": (
                    msg.sender.avatar_color
                    if msg.sender
                    else "#999999"
                ),
                "message": msg.message,
                "sent_at": msg.sent_at.isoformat() + "Z" if msg.sent_at else None,
                "is_read": msg.is_read,
                "public_seen": msg.public_seen
            }
            for msg in messages
        ]


@router.get("/users")
def get_users():
    with SessionLocal() as db:
        all_users = db.query(User).all()
        users = [
            {
                "username": u.username,
                "online": any(info["username"] == u.username for info in connections.values()),
                "last_seen":
                    (
                        u.last_seen.isoformat()+"Z"
                        if u.last_seen
                        else None
                    ),
                "avatar_color": u.avatar_color
            }
            for u in all_users
        ]
        return JSONResponse(users)
    

@router.get("/chats")
def get_chats(username: str):
    with SessionLocal() as db:

        user = db.query(User).filter(
            User.username == username
        ).first()

        if not user:
            return []

        chats = []

        # Get only user's recent chats
        recent_chats = (
            db.query(RecentChat)
            .filter(
                RecentChat.owner_id == user.id
            )
            .all()
        )

        for recent in recent_chats:

            # Find the other user in this room
            other_user = db.query(User).filter(
                User.id == recent.contact_id
            ).first()

            if not other_user:
                continue

            # Get room
            room = (
                db.query(ChatRoom)
                .filter(ChatRoom.room_type == "private")
                .filter(ChatRoom.users.any(id=user.id))
                .filter(ChatRoom.users.any(id=other_user.id))
                .first()
            )

            if not room:
                continue

            last_message = (
                db.query(Message)
                .filter(
                    Message.room_id == room.id,
                    Message.id > recent.cleared_message_id
                )
                .order_by(Message.sent_at.desc())
                .first()
            )
            

            # Unread message count
            read_status = (
                db.query(ChatReadStatus)
                .filter(
                    ChatReadStatus.user_id == user.id,
                    ChatReadStatus.room_id == room.id
                )
                .first()
            )

            last_read_id = (
                read_status.last_read_message_id
                if read_status
                else 0
            )


            unread_count = (
                db.query(Message)
                .filter(
                    Message.room_id == room.id,
                    Message.id > last_read_id,
                    Message.sender_id != user.id   # don't count my own messages
                )
                .count()
            )


            chats.append({
                "user_id": other_user.id,
                "username": other_user.username,
                "avatar_color": other_user.avatar_color,
                "last_message": last_message.message if last_message else "",
                "last_sender": (
                    "You"
                    if last_message and last_message.sender.username == username
                    else last_message.sender.username
                    if last_message and last_message.sender
                    else ""
                ),
                "sent_at": (
                    last_message.sent_at.isoformat() + "Z"
                    if last_message else None
                ),
                "unread_count": unread_count
            })

        # Newest chat first
        chats.sort(
            key=lambda x: x["sent_at"] or "",
            reverse=True
        )

        return chats
    
# (+)
@router.post("/mark_read")
async def mark_read(
    username: str,
    receiver: str
):

    with SessionLocal() as db:

        user = db.query(User).filter(
            User.username == username
        ).first()


        if not user:
            return {"success": False}


        room = get_or_create_private_room(
            db,
            username,
            receiver
        )


        latest_message = (
            db.query(Message)
            .filter(Message.room_id == room.id)
            .order_by(Message.id.desc())
            .first()
        )


        if latest_message:

            status = (
                db.query(ChatReadStatus)
                .filter(
                    ChatReadStatus.user_id == user.id,
                    ChatReadStatus.room_id == room.id
                )
                .first()
            )


            if not status:

                status = ChatReadStatus(
                    user_id=user.id,
                    room_id=room.id
                )

                db.add(status)


            status.last_read_message_id = latest_message.id

            # mark messages from the other user as seen
            db.query(Message).filter(
                Message.room_id == room.id,
                Message.sender_id != user.id,
                Message.id <= latest_message.id
            ).update(
                {
                    Message.is_read: 1
                },
                synchronize_session=False
            )

            db.commit()

            await broadcast_message_seen(
                sender=receiver,
                viewer=username,
                room_id=room.id
            )

            await notify_seen(
            sender=receiver,
            reader=username,
            room_id=room.id,
            last_read_id=latest_message.id
        )

        return {
            "success": True
        }
# (+)
async def broadcast_message_seen(sender, viewer, room_id):

    for conn, info in list(connections.items()):

        if info["username"] == sender:

            await conn.send_text(json.dumps({
                "type": "message_seen",
                "room_id": room_id,
                "viewer": viewer
            }))


@router.post("/start-chat")
async def start_chat(
    username: str = Query(...),
    receiver: str = Query(...)
):

    with SessionLocal() as db:

        room = get_or_create_private_room(
            db,
            username,
            receiver
        )


    # notify both users
    await broadcast_chat_created(
        username,
        receiver
    )


    return {
        "success": True
    }

async def broadcast_chat_created(user1, user2):

    print("SEND NEW CHAT TO:", user1, user2)

    for conn, info in list(connections.items()):
        print("CONNECTED USER:", info["username"])
        
        if info["username"] in [user1, user2]:

            await conn.send_text(json.dumps({
                "type":"new_chat",
                "username": (
                    user2 
                    if info["username"] == user1
                    else user1
                )
            }))


# for adding new user
@router.get("/search_users")
def search_users(username: str, q: str = ""):
    with SessionLocal() as db:

        current_user = db.query(User).filter(
            User.username == username
        ).first()

        users = (
            db.query(User)
            .filter(User.username.ilike(f"%{q}%"))
            .filter(User.username != username)
            .all()
        )

        recent_ids = {
            r.contact_id
            for r in db.query(RecentChat)
            .filter(
                RecentChat.owner_id == current_user.id
            )
            .all()
        }

        return [
            {
                "username": u.username,
                "avatar_color": u.avatar_color,
                "online": any(
                    info["username"] == u.username
                    for info in connections.values()
                ),

                "is_recent": u.id in recent_ids
            }
            for u in users
        ]
    

# search and add to recent chat
@router.post("/add_recent_chat")
async def add_recent_chat(
    username: str,
    contact_username: str
):
    with SessionLocal() as db:

        owner = db.query(User).filter(
            User.username == username
        ).first()

        contact = db.query(User).filter(
            User.username == contact_username
        ).first()


        if not owner or not contact:
            return {
                "success": False,
                "message": "User not found"
            }

        # create private room immediately
        room = get_or_create_private_room(
            db,
            username,
            contact_username
        )

        # prevent duplicate
        existing = db.query(RecentChat).filter(
            RecentChat.owner_id == owner.id,
            RecentChat.contact_id == contact.id
        ).first()


        if existing:

            existing.cleared_message_id = 0

            db.commit()

            return {
                "success": True,
                "message": "Chat restored"
            }


        # Add for User A
        new_chat1 = RecentChat(
            owner_id=owner.id,
            contact_id=contact.id
        )

        # Add for User B
        new_chat2 = RecentChat(
            owner_id=contact.id,
            contact_id=owner.id
        )

        db.add_all([
            new_chat1,
            new_chat2
        ])

        db.commit()

        await broadcast_chat_created(
            owner.username,
            contact.username
        )

        return {
            "success": True,
            "message": "User added"
        }


# private chat history clear
@router.post("/clear_chat")
def clear_chat(
    username: str,
    contact_username: str
):

    with SessionLocal() as db:

        user = db.query(User).filter(
            User.username == username
        ).first()

        contact = db.query(User).filter(
            User.username == contact_username
        ).first()


        if not user or not contact:
            return {
                "success": False
            }


        # get private room
        room = get_or_create_private_room(
            db,
            username,
            contact_username
        )


        # find user's recent chat record
        recent = db.query(RecentChat).filter(
            RecentChat.owner_id == user.id,
            RecentChat.contact_id == contact.id
        ).first()


        if not recent:
            return {
                "success": False,
                "message": "Recent chat not found"
            }


        # get latest message id
        last_message = (
            db.query(Message)
            .filter(Message.room_id == room.id)
            .order_by(Message.id.desc())
            .first()
        )


        if last_message:
            recent.cleared_message_id = last_message.id
        else:
            recent.cleared_message_id = 0


        db.commit()


        return {
            "success": True
        }