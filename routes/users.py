from fastapi import APIRouter, Request
from database import SessionLocal
from models import User

router = APIRouter()

@router.get("/users")
def get_users(request: Request):

    current_username = request.session.get("username")

    db = SessionLocal()

    users = db.query(User).all()

    db.close()

    return [
        {
            "id": user.id,
            "username": user.username
        }
        for user in users
        if user.username != current_username
    ]