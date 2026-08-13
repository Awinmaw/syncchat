from sqlalchemy import Table, Column, Integer, String, DateTime, ForeignKey
from database import Base
import datetime
from sqlalchemy.orm import relationship

print("MODELS FILE:", __file__)

class User(Base):
    __tablename__ = "users"
    #print("Creating User class")
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    password = Column(String(255))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    avatar_color = Column(String(20), nullable=True)
    
    # Last offline time
    last_seen = Column(DateTime, nullable=True)

    messages = relationship("Message", back_populates="sender")
    recent_contacts = relationship(
        "RecentChat",
        foreign_keys="RecentChat.owner_id",
        back_populates="owner",
        cascade="all, delete-orphan"
    )


# association table
chatroom_users = Table(
    "chatroom_users",
    Base.metadata,
    Column("chatroom_id", Integer, ForeignKey("chat_rooms.id")),
    Column("user_id", Integer, ForeignKey("users.id"))
)


class ChatRoom(Base):
    __tablename__ = "chat_rooms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    room_type = Column(String(20), nullable=False)  # "public" or "private
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    messages = relationship("Message", back_populates="room")
    users = relationship("User", secondary=chatroom_users, backref="chatrooms")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)

    room_id = Column(Integer, ForeignKey("chat_rooms.id"))

    sender_id = Column(Integer, ForeignKey("users.id"))

    message = Column(String(1000))

    sent_at = Column(
        DateTime,
        default=datetime.datetime.utcnow
    )

    # read status
    is_read = Column(
        Integer,
        default=0
    )
    # read status for group chat
    public_seen = Column(
        Integer,
        default=0
    )

    sender = relationship("User", back_populates="messages")

    room = relationship("ChatRoom", back_populates="messages")



class RecentChat(Base):
    __tablename__ = "recent_chats"

    id = Column(Integer, primary_key=True, index=True)

    owner_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    contact_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.datetime.utcnow
    )

    cleared_message_id = Column(
        Integer,
        nullable=True,
        default=0
    )

    # user(A)
    owner = relationship(
        "User",
        foreign_keys=[owner_id],
        back_populates="recent_contacts"
    )

    # user(B)
    contact = relationship(
        "User",
        foreign_keys=[contact_id],
    )


class ChatReadStatus(Base):
    __tablename__ = "chat_read_status"

    id = Column(Integer, primary_key=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    room_id = Column(
        Integer,
        ForeignKey("chat_rooms.id"),
        nullable=False
    )

    last_read_message_id = Column(
        Integer,
        default=0
    )
