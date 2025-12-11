from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class CommandRequest(BaseModel):
    command_text: str

class RuleCreate(BaseModel):
    pattern: str
    action: str

class RuleResponse(RuleCreate):
    id: int
    class Config:
        from_attributes = True

class UserCreate(BaseModel):
    username: str
    role: str

class CommandResponse(BaseModel):
    status: str
    new_balance: int
    message: str

class LogResponse(BaseModel):
    user_id: int
    username: str  
    command_text: str
    status: str
    reason: str
    timestamp: datetime
    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    username: str
    credits: int

class UserDetail(BaseModel):
    id: int
    username: str
    role: str
    credits: int
    api_key: str
    class Config:
        from_attributes = True

# Update UserCreate to include credits
class UserCreate(BaseModel):
    username: str
    role: str
    credits: int = 100 # Default if not provided