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
    command_text: str
    status: str
    reason: str
    timestamp: datetime
    class Config:
        from_attributes = True