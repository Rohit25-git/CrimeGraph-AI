from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, List
import jwt
import bcrypt

from backend.app.database.postgres import get_db
from backend.app.models.database_models import User, AuditLog
from backend.app.schemas.schemas import UserCreate, UserResponse, Token
from backend.app.config import settings

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def get_password_hash(password: str) -> str:
    passwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(passwd_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    plain_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(plain_bytes, hashed_bytes)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
        
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

class RoleChecker:
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, user: User = Depends(get_current_user)) -> User:
        if user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' is not authorized. Required: one of {self.allowed_roles}"
            )
        return user

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user_in: UserCreate, db: Session = Depends(get_db)):
    # Check if exists
    db_user = db.query(User).filter(User.username == user_in.username).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    hashed_pwd = get_password_hash(user_in.password)
    user = User(
        username=user_in.username,
        hashed_password=hashed_pwd,
        role=user_in.role or "VIEWER"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Audit log
    log = AuditLog(
        action="register",
        resource=f"user:{user.username}",
        result="SUCCESS",
        timestamp=datetime.utcnow()
    )
    db.add(log)
    db.commit()
    
    return user

@router.post("/login", response_model=Token)
def login_user(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        # Audit log failure
        log = AuditLog(
            action="login",
            resource=f"user:{form_data.username}",
            result="FAILURE_CREDENTIALS",
            timestamp=datetime.utcnow()
        )
        db.add(log)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role, "user_id": user.id}
    )
    
    # Audit log success
    log = AuditLog(
        user_id=user.id,
        action="login",
        resource=f"user:{user.username}",
        result="SUCCESS",
        timestamp=datetime.utcnow()
    )
    db.add(log)
    db.commit()
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.get("/demo-personas")
def get_demo_personas():
    return [
        {
            "id": "admin",
            "name": "System Administrator",
            "username": "admin",
            "password": "admin123",
            "role": "ADMIN",
            "title": "Platform Chief Administrator & Security Officer",
            "department": "National Cyber Crime Threat Analytics Directorate",
            "clearance": "LEVEL 5+ — SUPER ADMIN // ROOT CLEARANCE",
            "badge": "SYS-ROOT-01",
            "description": "Unrestricted administrative root authority: user provisioning, ML model deployment, system health audits, Neo4j/Postgres database access, and full investigative controls."
        },
        {
            "id": "investigator",
            "name": "Vikram Rathore",
            "username": "investigator",
            "password": "password",
            "role": "ADMIN",
            "title": "Lead Cyber & Anti-Narcotics Investigator",
            "department": "Special Operations / CID Crime Branch",
            "clearance": "LEVEL 4 — RESTRICTED / TOP SECRET",
            "badge": "CID-9402",
            "description": "Full administrative clearance across graph exploration, entity deduplication, case management, and AI prompt engineering."
        },
        {
            "id": "analyst",
            "name": "Neha Deshmukh",
            "username": "analyst",
            "password": "password",
            "role": "ANALYST",
            "title": "Senior Financial & Network Intelligence Analyst",
            "department": "Financial Crimes & Hawala Tracking Unit",
            "clearance": "LEVEL 3 — SECRET // FININT",
            "badge": "FIU-2811",
            "description": "Specialized in financial transaction volatility, CDR call graph analysis, Louvain community metrics, and Isolation Forest ML anomaly mining."
        },
        {
            "id": "forensics",
            "name": "Aditya Verma",
            "username": "forensics",
            "password": "password",
            "role": "FORENSIC_OFFICER",
            "title": "Digital Forensics & Chain-of-Custody Officer",
            "department": "Cyber Forensics Laboratory (FSL)",
            "clearance": "LEVEL 3 — EVIDENCE VAULT ACCREDITED",
            "badge": "FSL-1049",
            "description": "Handles multi-source ingestion, SHA-256 cryptographic evidence hashing, FIR/surveillance extraction verification, and provenance audit trails."
        },
        {
            "id": "commander",
            "name": "Rajeshwar Singh (IPS)",
            "username": "commander",
            "password": "password",
            "role": "COMMANDER",
            "title": "Supervisory Joint Commissioner of Police",
            "department": "Executive Crime Operations Directorate",
            "clearance": "LEVEL 5 — EXECUTIVE COMMAND",
            "badge": "IPS-0041",
            "description": "Executive command oversight, case priority validation, responsible AI governance audit, and judicial presentation reviews."
        },
        {
            "id": "field_agent",
            "name": "Suresh Kale",
            "username": "field_agent",
            "password": "password",
            "role": "FIELD_AGENT",
            "title": "Field Surveillance & Ground Operative",
            "department": "Anti-Extortion & Tactical Field Squad",
            "clearance": "LEVEL 2 — TACTICAL FIELD SENSITIVE",
            "badge": "ATS-7734",
            "description": "Fast mobile query mode for real-time subject identity checks, CCTNS criminal convictions lookup, and vehicle/location tracking."
        }
    ]

