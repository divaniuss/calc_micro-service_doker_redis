import os
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import jwt
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
security = HTTPBearer()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"

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
def calculate(request: CalcRequest, username: str = Depends(verify_token)):
    allowed_chars = set("1234567890+-*/")
    expression = request.expression.replace(" ", "")

    if not set(expression).issubset(allowed_chars):
        print("validation failed")
        raise HTTPException(status_code=400, detail="invalid characters")

    try:
        result = eval(expression)
        print("calc success")
        return {"result": result}
    except ZeroDivisionError:
        print("calc error")
        raise HTTPException(status_code=400, detail="division by zero")
    except Exception:
        print("calc error")
        raise HTTPException(status_code=400, detail="invalid expression")