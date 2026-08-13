from fastapi import FastAPI
from database import engine, Base
import models         
from routes import auth
from routes import chat
from routes import users
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

import os
print(os.path.abspath("syncchat.db")) # show the absolute path of the database file

app = FastAPI()

# Create tables if they don’t exist
Base.metadata.create_all(bind=engine)

# Allow Cloudflare Tunnel / external browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.add_middleware(
    SessionMiddleware,
    secret_key="syncchat_secret_key"
)

# Serve files from the "static" folder
app.mount("/static", StaticFiles(directory="static"), name="static")

# Routers
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(users.router)

#app.add_middleware(
#    SessionMiddleware,
#    secret_key="syncchat_secret_key"
#)

@app.get("/")
def home():
    return {"message": "Server is running"}

# CREATE DATABASE + TABLES
Base.metadata.create_all(bind=engine)


from database import SessionLocal
from models import ChatRoom

def create_default_room():
    db = SessionLocal()

    room = db.query(ChatRoom).filter(
        ChatRoom.name == "Public"
    ).first()

    if room is None:
        public_room = ChatRoom(
            name="Public",
            room_type="public"
        )

        db.add(public_room)
        db.commit()

    db.close()

create_default_room()

