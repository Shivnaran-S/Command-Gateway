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
            models.Rule(pattern=r":(){ :|:& };:", action="AUTO_REJECT"),
            models.Rule(pattern=r"rm\s+-rf\s+/", action="AUTO_REJECT"),
            models.Rule(pattern=r"mkfs\.", action="AUTO_REJECT"),
            models.Rule(pattern=r"git\s+(status|log|diff)", action="AUTO_ACCEPT"),
            models.Rule(pattern=r"^(ls|cat|pwd|echo)", action="AUTO_ACCEPT"),
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
    if user.credits > 0:
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

@app.get("/logs", response_model=List[schemas.LogResponse])
def get_logs(
    x_api_key: str = Header(...),
    role_filter: str = "all",      # 'all', 'mine', 'other_admins', 'users'
    status_filter: str = "all",    # 'all', 'executed', 'rejected'
    target_api_key: str = None,    # Filter by specific user API key
    sort_order: str = "desc",      # 'asc', 'desc'
    db: Session = Depends(database.get_db)
):
    current_user = get_user_by_key(x_api_key, db)
    
    # Base query joining User to access roles
    query = db.query(models.CommandLog).join(models.User)

    # --- Role & Permission Filtering ---
    if current_user.role != "admin":
        # Regular users can ONLY see their own logs
        query = query.filter(models.CommandLog.user_id == current_user.id)
    else:
        # Admin Filters
        if target_api_key:
            target = db.query(models.User).filter(models.User.api_key == target_api_key).first()
            if not target:
                # Return empty if invalid key provided to filter
                return [] 
            query = query.filter(models.CommandLog.user_id == target.id)
        
        elif role_filter == "mine":
            query = query.filter(models.CommandLog.user_id == current_user.id)
        elif role_filter == "users":
            query = query.filter(models.User.role == "member")
        elif role_filter == "other_admins":
            query = query.filter(models.User.role == "admin", models.User.id != current_user.id)
    
    # --- Status Filtering ---
    if status_filter == "executed":
        query = query.filter(models.CommandLog.status == "EXECUTED")
    elif status_filter == "rejected":
        query = query.filter(models.CommandLog.status != "EXECUTED") # Catch REJECTED, BLOCKED, NO_CREDITS

    # --- Sorting ---
    if sort_order == "asc":
        query = query.order_by(models.CommandLog.timestamp.asc())
    else:
        query = query.order_by(models.CommandLog.timestamp.desc())

    return query.all()

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
def create_user(user_data: schemas.UserCreate, x_api_key: str = Header(...), db: Session = Depends(database.get_db)):
    admin = get_user_by_key(x_api_key, db)
    if admin.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    # Check if username exists
    if db.query(models.User).filter(models.User.username == user_data.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")

    new_key = str(uuid.uuid4())
    new_user = models.User(
        username=user_data.username, 
        role=user_data.role, 
        api_key=new_key,
        credits=user_data.credits # Now using the input credits
    )
    db.add(new_user)
    db.commit()
    return {"username": new_user.username, "api_key": new_key}

# --- User Management Endpoints ---

@app.get("/users/search", response_model=schemas.UserDetail)
def get_user_details(target_key: str, x_api_key: str = Header(...), db: Session = Depends(database.get_db)):
    admin = get_user_by_key(x_api_key, db)
    if admin.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    target = get_user_by_key(target_key, db) # Reusing helper (will raise 401 if invalid, which is fine)
    return target

@app.put("/users/update")
def update_user(target_key: str, update_data: schemas.UserUpdate, x_api_key: str = Header(...), db: Session = Depends(database.get_db)):
    admin = get_user_by_key(x_api_key, db)
    if admin.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
        
    target = db.query(models.User).filter(models.User.api_key == target_key).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    
    target.username = update_data.username
    target.credits = update_data.credits
    db.commit()
    return {"message": "User updated"}

@app.delete("/users/delete")
def delete_user(target_key: str, x_api_key: str = Header(...), db: Session = Depends(database.get_db)):
    admin = get_user_by_key(x_api_key, db)
    if admin.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
        
    target = db.query(models.User).filter(models.User.api_key == target_key).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Optional: Delete associated logs first or rely on cascade
    db.query(models.CommandLog).filter(models.CommandLog.user_id == target.id).delete()
    db.delete(target)
    db.commit()
    return {"message": "User deleted"}