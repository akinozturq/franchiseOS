from datetime import datetime, timedelta, timezone
from typing import Optional, List
import bcrypt
import jwt
from fastapi import Depends, HTTPException, status, Query, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.models.user import User
from backend.app.models.branch import Branch

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        pwd_bytes = plain_password.encode("utf-8")[:72]
        hash_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt

def apply_tenant_context(db: Session, user: User, branch_id: Optional[int] = None):
    """
    Sets PostgreSQL RLS session variables:
    - Switches role to 'franchise_app'
    - Configures app.current_branch_id and app.is_franchisor_admin
    """
    try:
        db.execute(text("SET ROLE franchise_app;"))
        if user.role == "FRANCHISOR_ADMIN" and branch_id is None:
            db.execute(text("SET app.is_franchisor_admin = 'true';"))
            db.execute(text("SET app.current_branch_id = '';"))
        else:
            db.execute(text("SET app.is_franchisor_admin = 'false';"))
            target_bid = str(branch_id if branch_id is not None else (user.branch_id or ""))
            db.execute(text(f"SET app.current_branch_id = '{target_bid}';"))
    except Exception:
        pass

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Kimlik doğrulanamadı. Lütfen tekrar giriş yapın.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
        
    user = db.query(User).filter(User.username == username).first()
    if user is None or not user.is_active:
        raise credentials_exception
    
    apply_tenant_context(db, user)
    return user

def require_roles(*allowed_roles: str):
    """
    Dependency factory to enforce RBAC permissions on endpoints.
    Returns 403 Forbidden if user's role is not in allowed_roles.
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bu işlem için yetkiniz bulunmamaktadır."
            )
        return current_user
    return role_checker

def get_active_branch_id(
    branch_id: Optional[int] = Query(None, description="Hedef Bayi ID (Franchisor Admin için)"),
    x_branch_id: Optional[int] = Header(None, alias="X-Branch-Id", description="Hedef Bayi ID (Header)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> int:
    """
    Resolves the active branch_id for the current request.
    - Franchisor Admin: Can specify branch via query or header; defaults to first active branch.
    - Bayi Admin & Viewer: Bound strictly to user.branch_id. Attempting to access another branch yields 403.
    Also updates PostgreSQL RLS session variables for the resolved branch.
    """
    requested_id = branch_id if branch_id is not None else x_branch_id

    if current_user.role == "FRANCHISOR_ADMIN":
        if requested_id is not None:
            branch = db.query(Branch).filter(Branch.id == requested_id).first()
            if not branch:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Belirtilen bayi bulunamadı.")
            resolved_id = branch.id
        else:
            first_branch = db.query(Branch).filter(Branch.is_active == True).order_by(Branch.id.asc()).first()
            if not first_branch:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sistemde kayıtlı bayi bulunamadı.")
            resolved_id = first_branch.id
    else:
        if not current_user.branch_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Kullanıcı hesabınıza atanmış bir bayi bulunmamaktadır."
            )
        if requested_id is not None and requested_id != current_user.branch_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Farklı bir bayinin verisine erişim yetkiniz yoktur."
            )
        resolved_id = current_user.branch_id

    # Update RLS tenant context for this specific resolved branch
    apply_tenant_context(db, current_user, resolved_id)
    return resolved_id
