from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.middleware.cors import CORSMiddleware

from db.session import Base, engine, get_db
import db.models

from admin.routers import admin_router
from routers import auth, profiles, users

app = FastAPI(title="Stylometr API")


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "ok",
            "database": "ok"
        }
    except Exception:
        return {
            "status": "error",
            "database": "down"
        }


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(profiles.router)
app.include_router(admin_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
