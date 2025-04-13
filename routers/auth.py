from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
import logging
from bson import ObjectId
from core.database import get_db_dependency
from core.auth import create_access_token, verify_password, get_password_hash
from models.user import UserInDB, UserCreate, UserResponse
from models.auth import AuthResponse
from middleware.auth import get_current_active_user

logger = logging.getLogger(__name__)
router = APIRouter(tags=["auth"])

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

@router.post("/register", response_model=AuthResponse)
async def register(
    user_data: UserCreate,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    """Register new user"""
    try:
        # Normalize email
        email = user_data.email.lower().strip()
        
        # Check if user exists
        if await db.users.find_one({"email": email}):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Create user document
        user_dict = user_data.model_dump()
        user_dict.update({
            "email": email,
            "password": get_password_hash(user_data.password),
            "created_at": datetime.utcnow(),
            "role": "user",
            "is_active": True,
            "preferences": {},
            "last_login": None
        })

        # Insert into database
        result = await db.users.insert_one(user_dict)
        user_dict["id"] = str(result.inserted_id)

        # Create access token
        token_data = {
            "sub": email,
            "role": "user"
        }
        access_token = create_access_token(data=token_data)

        # Create response
        user_response = UserResponse(
            id=user_dict["id"],
            email=email,
            name=user_dict["name"],
            role=user_dict["role"],
            is_active=user_dict["is_active"],
            created_at=user_dict["created_at"],
            last_login=user_dict["last_login"],
            preferences=user_dict["preferences"]
        )

        logger.info(f"Registration successful - User: {email}")
        return AuthResponse(
            access_token=access_token,
            token_type="bearer",
            user=user_response
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/admin/login", response_model=AuthResponse)
async def admin_login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    """Admin login endpoint"""
    try:
        email = form_data.username.lower().strip()
        logger.info(f"Admin login attempt - Email: {email}")
        
        # Find user by email
        user_dict = await db.users.find_one({"email": email})
        if not user_dict or user_dict.get("role") != "admin":
            logger.warning(f"Admin login failed: Invalid credentials or not admin - {email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )

        # Convert ObjectId to string and create user instance
        user_dict["id"] = str(user_dict.pop("_id"))
        user = UserInDB(**user_dict)

        if not verify_password(form_data.password, user.password):
            logger.warning(f"Admin login failed: Invalid password - {email}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )

        # Update last login
        current_time = datetime.utcnow()
        await db.users.update_one(
            {"_id": ObjectId(user.id)},
            {"$set": {"last_login": current_time}}
        )

        # Create admin token with extended privileges
        token_data = {
            "sub": user.email,
            "role": "admin"
        }
        access_token = create_access_token(data=token_data)

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

        logger.info(f"Admin login successful - User: {email}")
        return AuthResponse(
            access_token=access_token,
            token_type="bearer",
            user=user_response
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin login failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )

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
