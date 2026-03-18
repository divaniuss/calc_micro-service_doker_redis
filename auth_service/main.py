import os
import json
import hashlib
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import jwt
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
import redis.asyncio as redis
from redis.exceptions import RedisError
from contextlib import asynccontextmanager

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
MONGO_URL = os.getenv("MONGO_URL")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

mongo_client = AsyncIOMotorClient(MONGO_URL)
db = mongo_client.test
collection = db.calc_docker

redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True, socket_timeout=1)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        await redis_client.ping()
        print("redis connected")
    except RedisError:
        print("redis error")

    try:
        await mongo_client.admin.command('ping')
        print("mongo connected")
    except Exception:
        print("mongo error")

    yield

    await redis_client.close()
    mongo_client.close()


app = FastAPI(lifespan=lifespan)


class UserBase(BaseModel):
    username: str
    password: str = Field(min_length=8)


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def create_jwt(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=24)
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
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    await collection.insert_one(user_doc)

    log_entry = {
        "username": user.username,
        "action": "register",
        "status": "success",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    await redis_client.lpush("auth_logs", json.dumps(log_entry))

    print("register success")
    return {"status": "success"}


@app.post("/login")
async def login(user: UserBase):
    db_user = await collection.find_one({"username": user.username})
    if not db_user:
        print("auth failed")
        raise HTTPException(status_code=400, detail="invalid credentials")

    if db_user["password"] != hash_password(user.password):
        print("auth failed")
        raise HTTPException(status_code=400, detail="wrong password")

    token = create_jwt(user.username)

    log_entry = {
        "username": user.username,
        "action": "login",
        "status": "success",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    await redis_client.lpush("auth_logs", json.dumps(log_entry))

    print("login success")
    return {"access_token": token, "token_type": "bearer"}