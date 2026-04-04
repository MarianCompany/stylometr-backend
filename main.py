from fastapi import FastAPI

from db.session import Base, engine
import db.models

from routers import users

app = FastAPI(title="Stylometr API")


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)


@app.get("/ping")
def ping():
    return {"status": "ok"}

app.include_router(users.router, prefix="/users", tags=["users"])