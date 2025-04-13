from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from core.config import get_settings
from models.user import UserCreate, UserResponse, UserInDB
from models.auth import AuthResponse
from core.auth import verify_password, get_password_hash, create_access_token
from motor.motor_asyncio import AsyncIOMotorDatabase
from core.database import get_db_dependency
import logging
from bson import ObjectId
from middleware.auth import get_current_active_user
from services.mongodb import get_mongodb

logger = logging.getLogger(__name__)
router = APIRouter(tags=["auth"])
settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

@router.post("/token", response_model=AuthResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    """Login user and return access token"""
    try:
        # Normalize email
        email = form_data.username.lower().strip()
        logger.info(f"Login attempt - Email: {email}")
        
        # Find user by email
        user_dict = await db.users.find_one({"email": email})
        if not user_dict:
            logger.warning(f"Login failed: User not found - {email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )

        # Convert ObjectId to string and create user instance
        user_dict["id"] = str(user_dict.pop("_id"))
        user = UserInDB(**user_dict)

        # Verify password
        if not verify_password(form_data.password, user.password):
            logger.warning(f"Login failed: Invalid password - {email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )

        # Update last login
        current_time = datetime.utcnow()
        await db.users.update_one(
            {"_id": ObjectId(user.id)},
            {"$set": {"last_login": current_time}}
        )

        # Create access token
        token_data = {
            "sub": user.email,
            "role": user.role
        }
        access_token = create_access_token(data=token_data)

        # Create response
        user_response = UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
            last_login=current_time,
            preferences=user.preferences
        )

        logger.info(f"Login successful - User: {email}")
        return AuthResponse(
            access_token=access_token,
            token_type="bearer",
            user=user_response
        )

    except Exception as e:
        logger.error(f"Login failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )

@router.post("/register", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate):
    db = get_mongodb()
    
    # Check if user already exists
    existing_user = await db.find_one("users", {"$or": [
        {"email": user_data.email},
        {"username": user_data.username}
    ]})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or username already registered"
        )
    
    # Create user document
    user_dict = user_data.model_dump(exclude={"password"})
    user_dict["hashed_password"] = get_password_hash(user_data.password)
    user_dict["created_at"] = datetime.utcnow()
    user_dict["role"] = "user"
    user_dict["preferences"] = {}
    
    # Insert into database
    result = await db.insert_one("users", user_dict)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_data.email},
        expires_delta=access_token_expires
    )
    
    # Get created user for response
    created_user = await db.find_one("users", {"_id": result})
    if not created_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User created but failed to retrieve"
        )
    
    # Return token and user data
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse(**created_user)
    }

@router.post("/admin/login", response_model=Dict[str, Any])
async def admin_login(form_data: OAuth2PasswordRequestForm = Depends()):
    db = get_mongodb()
    user = await db.find_one("users", {
        "email": form_data.username,
        "role": "admin"
    })
    
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if user.get("disabled", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin account is disabled"
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["email"], "role": "admin"},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse(**user)
    }

@router.get("/verify", response_model=UserResponse, summary="Verify current token")
async def verify_token(
    current_user: UserInDB = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    """
    Verify the current token and return user info
    """
    try:
        logger.info(f"Token verification for user: {current_user.email}")
        return UserResponse(
            id=str(current_user.id),
            email=current_user.email,
            name=current_user.name,
            role=current_user.role,
            is_active=current_user.is_active,
            created_at=current_user.created_at,
            last_login=current_user.last_login,
            preferences=current_user.preferences
        )
    except Exception as e:
        logger.error(f"Error during token verification: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )

@router.get("/me", response_model=UserResponse, summary="Get current user info")
async def read_users_me(
    current_user: UserInDB = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    """Get current user information."""
    try:
        return UserResponse(
            id=str(current_user.id),
            email=current_user.email,
            name=current_user.name,
            role=current_user.role,
            is_active=current_user.is_active,
            created_at=current_user.created_at,
            last_login=current_user.last_login,
            preferences=current_user.preferences
        )
    except Exception as e:
        print(f"Error in read_users_me: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get user info"
        )
