from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, ForeignKey
from sqlalchemy.sql import func
from .database import Base
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    api_key = Column(String(100), unique=True, index=True)
    role = Column(String(20))  # 'admin' or 'member'
    credits = Column(Integer, default=100)

class Rule(Base):
    __tablename__ = "rules"
    id = Column(Integer, primary_key=True, index=True)
    pattern = Column(String(255))  # Regex pattern
    action = Column(String(20))    # 'AUTO_ACCEPT', 'AUTO_REJECT'

class CommandLog(Base):
    __tablename__ = "command_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    command_text = Column(String(255))
    status = Column(String(50))    # 'executed', 'rejected'
    reason = Column(String(50))
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")

    @property
    def username(self):
        return self.user.username if self.user else "Unknown"