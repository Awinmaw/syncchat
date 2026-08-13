from database import SessionLocal
from models import User, ChatRoom
from sqlalchemy.orm import joinedload

def get_or_create_private_room(db, user1_name, user2_name):
    user1 = db.query(User).filter(User.username == user1_name).first()
    user2 = db.query(User).filter(User.username == user2_name).first()

    if not user1 or not user2:
        raise ValueError("One or both users not found")

    # check both users are in the room
    room = (
        db.query(ChatRoom)
        .options(joinedload(ChatRoom.users))
        .filter(ChatRoom.room_type == "private")
        .filter(ChatRoom.users.any(User.id == user1.id))
        .filter(ChatRoom.users.any(User.id == user2.id))
        .first()
    )
    
    if not room:
        room = ChatRoom(
            # create new private room
            name=f"private-{user1.username}-{user2.username}",
            room_type="private"
        )
        db.add(room)
        db.commit()
        db.refresh(room)

        # attach both users before committing again
        room.users.append(user1)
        room.users.append(user2)
        db.commit()   # ✅ commit again after adding users
        db.refresh(room)

    return room
