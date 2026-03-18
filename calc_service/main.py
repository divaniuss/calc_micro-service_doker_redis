import os
import json
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import jwt
from dotenv import load_dotenv
import redis.asyncio as redis
from redis.exceptions import RedisError
from contextlib import asynccontextmanager

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True, socket_timeout=1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await redis_client.ping()
        print("redis connected")
    except RedisError:
        print("redis error")
    yield
    await redis_client.close()


app = FastAPI(lifespan=lifespan)
security = HTTPBearer()


class CalcRequest(BaseModel):
    expression: str


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        print("token valid")
        return payload["sub"]
    except jwt.ExpiredSignatureError:
        print("token expired")
        raise HTTPException(status_code=401, detail="token expired")
    except jwt.InvalidTokenError:
        print("token invalid")
        raise HTTPException(status_code=401, detail="token invalid")


@app.post("/calc")
async def calculate(request: CalcRequest, username: str = Depends(verify_token)):
    allowed_chars = set("1234567890+-*/")
    expression = request.expression.replace(" ", "")

    if not set(expression).issubset(allowed_chars):
        print("validation failed")
        raise HTTPException(status_code=400, detail="invalid characters")

    try:
        result = eval(expression)

        log_entry = {
            "username": username,
            "expression": expression,
            "result": result,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await redis_client.lpush("calc_logs", json.dumps(log_entry))

        print("calc success")
        return {"result": result}
    except ZeroDivisionError:
        print("calc error")
        raise HTTPException(status_code=400, detail="division by zero")
    except Exception:
        print("calc error")
        raise HTTPException(status_code=400, detail="invalid expression")