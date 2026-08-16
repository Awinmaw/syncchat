import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

#DATABASE_URL = "sqlite:///./syncchat.db"
#DATABASE_URL = "sqlite:////data/syncchat.db"

if os.getenv("RAILWAY_ENVIRONMENT"):
    DATABASE_URL = "sqlite:////data/syncchat.db"
else:
    DATABASE_URL = "sqlite:///./syncchat.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
    #pool_size=20,        # default is 5
    #max_overflow=40,     # default is 10
    #pool_timeout=30,
    #pool_recycle=1800
)


SessionLocal = sessionmaker(
    bind=engine, 
    autoflush=False, 
    autocommit=False)

Base = declarative_base()