from fastapi import APIRouter, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Message, ChatRoom, User
import random

AVATAR_COLORS = [
    "#F44336",
    "#E91E63",
    "#9C27B0",
    "#673AB7",
    "#3F51B5",
    "#2196F3",
    "#03A9F4",
    "#0A5B9D",
    "#009688",
    "#4CAF50",
    "#8BC34A",
    "#FF9800",
    "#42332E",
    "#221713",
    "#000000",
]

router = APIRouter()

templates = Jinja2Templates(directory="templates")

#login page
@router.get("/login", response_class=HTMLResponse)
def login(request: Request):
    return templates.TemplateResponse("login.html", {
        "request": request
    })

#login validation
@router.post("/login")
def login_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    with SessionLocal() as db:
        user = db.query(User).filter(User.username == username).first()

        if not user:
            db.close()
            return HTMLResponse(
                content="""
                <script>
                    alert("User not found");
                    window.location.href = '/login';
                </script>
                """,
                status_code=200
            )

        if user.password != password:
            db.close()
            return HTMLResponse(
                content="""
                <script>
                    alert("Incorrect password");
                    window.location.href = '/login';
                </script>
                """,
                status_code=200
            )
        
        request.session["username"] = user.username
    #db.close()

    return RedirectResponse(
        url="/chat",    
        status_code=303
    )

#logout
@router.get("/logout")
def logout(request: Request):

    db = SessionLocal()

    user = db.query(User).filter(
        User.username == request.session.get("username")
    ).first()

    if user:
        user.online = False
        db.commit()

    request.session.clear()
    return RedirectResponse("/login", status_code=303)
    

#chat page
@router.get("/chat", response_class=HTMLResponse)
def chat(request: Request):

    username = request.session.get("username")

    if username is None:
        return RedirectResponse("/login")

    return templates.TemplateResponse(
        "chat.html",
        {
            "request": request,
            "username": username
        }
    )


#register page
@router.get("/register", response_class=HTMLResponse)
def register(request: Request):
    return templates.TemplateResponse("register.html", {
        "request": request
    })


# SAVE USER TO DATABASE
@router.post("/register")
def register_user(username: str = Form(...), password: str = Form(...)):

    #db = SessionLocal()
    with SessionLocal() as db:

        # check if user exists
        existing_user = db.query(User).filter(User.username == username).first()

        if existing_user:
            db.close()
            return {"message": "Username already exists"}

        # create new user
        new_user = User(
            username=username,
            password=password,
            avatar_color=random.choice(AVATAR_COLORS)
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        db.close()

    return RedirectResponse(url="/login", status_code=303)


