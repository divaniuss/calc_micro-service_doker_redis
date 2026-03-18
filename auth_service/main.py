import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from motor.motor_asyncio import AsyncIOMotorClient
import hashlib
import jwt
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

MONGO_URL = os.getenv("MONGO_URL")
client = AsyncIOMotorClient(MONGO_URL)
db = client.test
collection = db.calc_docker

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"


class UserBase(BaseModel):
    username: str
    password: str = Field(min_length=8)


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def create_jwt(username: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=24)
    payload = {"sub": username, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


@app.post("/register")
async def register(user: UserBase):
    existing_user = await collection.find_one({"username": user.username})
    if existing_user:
        print("user exists")
        raise HTTPException(status_code=400, detail="username taken")

    hashed_pw = hash_password(user.password)
    user_doc = {
        "username": user.username,
        "password": hashed_pw,
        "created_at": datetime.utcnow()
    }

    await collection.insert_one(user_doc)
    print("user registered")
    return {"status": "success"}


@app.post("/login")
async def login(user: UserBase):
    db_user = await collection.find_one({"username": user.username})
    if not db_user:
        print("auth failed(invalid credentials)")
        raise HTTPException(status_code=400, detail="invalid credentials")

    if db_user["password"] != hash_password(user.password):
        print("auth failed(wrong password)")
        raise HTTPException(status_code=400, detail="wrong password")

    token = create_jwt(user.username)
    print("token generated")
    return {"access_token": token, "token_type": "bearer"}