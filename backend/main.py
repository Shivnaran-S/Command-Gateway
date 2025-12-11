import re
import uuid
from fastapi import FastAPI, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from . import models, schemas, database
from typing import List

app = FastAPI()

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize DB
models.Base.metadata.create_all(bind=database.engine)

# --- Helpers ---
def get_user_by_key(api_key: str, db: Session):
    user = db.query(models.User).filter(models.User.api_key == api_key).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return user

# --- Startup Seed ---
@app.on_event("startup")
def seed_data():
    db = database.SessionLocal()
    # Seed Admin
    if not db.query(models.User).filter_by(username="admin").first():
        admin = models.User(username="admin", api_key="admin-secret-key", role="admin", credits=999)
        db.add(admin)
    
    # Seed Rules
    if db.query(models.Rule).count() == 0:
        rules = [
            models.Rule(pattern=r"^ls\s+.*", action="AUTO_ACCEPT"),
            models.Rule(pattern=r"rm\s+-rf\s+/", action="AUTO_REJECT"),
            models.Rule(pattern=r"^echo\s+.*", action="AUTO_ACCEPT"),
        ]
        db.add_all(rules)
    db.commit()
    db.close()

# --- Endpoints ---

@app.get("/me")
def get_me(x_api_key: str = Header(...), db: Session = Depends(database.get_db)):
    return get_user_by_key(x_api_key, db)

@app.post("/commands", response_model=schemas.CommandResponse)
def submit_command(
    cmd: schemas.CommandRequest, 
    x_api_key: str = Header(...), 
    db: Session = Depends(database.get_db)
):
    user = get_user_by_key(x_api_key, db)
    
    # Defaults
    final_status = "REJECTED"
    reason_msg = "Unknown Error"
    
    # 1. Match Rules
    rules = db.query(models.Rule).all()
    rule_action = "AUTO_REJECT" # Default safe fallback if no rule matches
    
    # Check if any rule matches
    matched = False
    for rule in rules:
        try:
            if re.search(rule.pattern, cmd.command_text):
                rule_action = rule.action
                matched = True
                break
        except re.error:
            continue

    # 2. Determine Logic
    if not matched:
        # Option A: Reject if no rule matches (Allowlist approach - Safer)
        final_status = "REJECTED"
        reason_msg = "No matching rule found"
        # Option B: Accept if no rule matches (Blocklist approach) -> For later coding!
        
    elif rule_action == "AUTO_REJECT":
        final_status = "REJECTED"
        reason_msg = "Blocked by security rule"
        
    elif rule_action == "AUTO_ACCEPT":
        if user.credits > 0:
            final_status = "EXECUTED"
            reason_msg = "Allowed by rule & credits available"
            # Deduct credit here
            user.credits -= 1
        else:
            final_status = "REJECTED"
            reason_msg = "Insufficient Credits"

    # 3. Save to DB
    try:
        log_entry = models.CommandLog(
            user_id=user.id,
            command_text=cmd.command_text,
            status=final_status,
            reason=reason_msg
        )
        db.add(log_entry)
        db.commit()
        
        return {
            "status": final_status,
            "new_balance": user.credits,
            "message": reason_msg
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database Error")

"""    
@app.post("/commands", response_model=schemas.CommandResponse)
def submit_command(
    cmd: schemas.CommandRequest, 
    x_api_key: str = Header(...), 
    db: Session = Depends(database.get_db)
):
    user = get_user_by_key(x_api_key, db)
    
    # 1. Check Credits
    if user.credits <= 0:
        raise HTTPException(status_code=403, detail="Insufficient credits")

    # 2. Match Rules
    rules = db.query(models.Rule).all()
    action = "AUTO_REJECT" # Default safe fallback
    
    for rule in rules:
        try:
            if re.search(rule.pattern, cmd.command_text):
                action = rule.action
                break
        except re.error:
            continue # Skip invalid regex rules if any slipped through

    # 3. Execution Logic (Transaction)
    try:
        final_status = "rejected"
        message = "Command blocked by rule."
        
        if action == "AUTO_ACCEPT":
            # "Mock" Execution
            user.credits -= 1
            final_status = "executed"
            message = f"Command '{cmd.command_text}' executed successfully."
        
        # Log entry
        log_entry = models.CommandLog(
            user_id=user.id,
            command_text=cmd.command_text,
            status=final_status,
            action_taken=action
        )
        db.add(log_entry)
        db.commit() # Succeeds only if both credit update (if any) and log succeed
        
        return {
            "status": final_status,
            "new_balance": user.credits,
            "message": message
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Transaction failed")
"""

@app.get("/logs", response_model=List[schemas.LogResponse])
def get_logs(x_api_key: str = Header(...), db: Session = Depends(database.get_db)):
    user = get_user_by_key(x_api_key, db)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return db.query(models.CommandLog).order_by(models.CommandLog.timestamp.desc()).all()

@app.post("/rules", response_model=schemas.RuleResponse)
def add_rule(rule: schemas.RuleCreate, x_api_key: str = Header(...), db: Session = Depends(database.get_db)):
    user = get_user_by_key(x_api_key, db)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Validate Regex
    try:
        re.compile(rule.pattern)
    except re.error:
        raise HTTPException(status_code=400, detail="Invalid Regex Pattern")
    
    new_rule = models.Rule(pattern=rule.pattern, action=rule.action)
    db.add(new_rule)
    db.commit()
    db.refresh(new_rule)
    return new_rule

@app.get("/rules", response_model=List[schemas.RuleResponse])
def get_rules(x_api_key: str = Header(...), db: Session = Depends(database.get_db)):
    get_user_by_key(x_api_key, db) # Auth check
    return db.query(models.Rule).all()

@app.post("/users/generate")
def create_user(username: str, role: str, x_api_key: str = Header(...), db: Session = Depends(database.get_db)):
    admin = get_user_by_key(x_api_key, db)
    if admin.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    new_key = str(uuid.uuid4())
    new_user = models.User(username=username, role=role, api_key=new_key)
    db.add(new_user)
    db.commit()
    return {"username": username, "api_key": new_key}