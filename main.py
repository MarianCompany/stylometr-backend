from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from db.session import Base, engine, get_db
import db.models

from routers import auth, users

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
