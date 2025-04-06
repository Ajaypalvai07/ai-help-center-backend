from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
import logging
from bson import ObjectId
from core.database import get_db_dependency
from core.auth import create_access_token, verify_password, get_password_hash
from models.user import UserInDB, UserCreate, UserResponse, AuthResponse
from middleware.auth import get_current_active_user

logger = logging.getLogger(__name__)
router = APIRouter(tags=["auth"])

@router.post("/token", response_model=AuthResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    """OAuth2 compatible token login"""
    try:
        logger.info(f"Login attempt for user: {form_data.username}")
        
        # Find user by email
        user_dict = await db.users.find_one({"email": form_data.username.lower().strip()})
        if not user_dict:
            logger.warning(f"Login failed: User not found - {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )

        # Convert ObjectId to string
        user_dict["id"] = str(user_dict.pop("_id"))
        
        try:
            user = UserInDB(**user_dict)
        except Exception as e:
            logger.error(f"Error creating UserInDB instance: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error processing user data"
            )

        # Verify password
        if not verify_password(form_data.password, user.password):
            logger.warning(f"Login failed: Invalid password for user - {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )

        # Update last login timestamp
        current_time = datetime.utcnow()
        await db.users.update_one(
            {"_id": ObjectId(user.id)},
            {"$set": {"last_login": current_time}}
        )
        
        # Create access token
        access_token = create_access_token(data={"sub": user.email})
        
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
        
        logger.info(f"Login successful for user: {user.email}")
        return AuthResponse(
            access_token=access_token,
            token_type="bearer",
            user=user_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during login: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during login"
        )

@router.post("/register", response_model=AuthResponse)
async def register(
    user_data: UserCreate,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    """Register a new user"""
    try:
        # Normalize email
        email = user_data.email.lower().strip()
        logger.info(f"Registration attempt for email: {email}")
        
        # Check if user exists
        existing_user = await db.users.find_one({"email": email})
        if existing_user:
            logger.warning(f"Registration failed: Email already exists - {email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Create user document
        user_dict = user_data.dict()
        user_dict.update({
            "email": email,  # Use normalized email
            "password": get_password_hash(user_data.password),
            "created_at": datetime.utcnow(),
            "role": "user",
            "is_active": True,
            "preferences": {},
            "last_login": None
        })

        # Insert into database
        try:
            result = await db.users.insert_one(user_dict)
            user_dict["id"] = str(result.inserted_id)
            logger.info(f"Created user document with ID: {user_dict['id']}")
        except Exception as e:
            logger.error(f"Database error during user creation: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user in database"
            )

        # Create access token
        access_token = create_access_token(data={"sub": email})
        
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
        
        logger.info(f"Registration successful for user: {email}")
        return AuthResponse(
            access_token=access_token,
            token_type="bearer",
            user=user_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during registration: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user account"
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
