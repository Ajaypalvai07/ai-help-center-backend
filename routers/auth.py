from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime
import logging
from bson import ObjectId
from core.database import get_db_dependency
from core.auth import create_access_token, verify_password
from models.user import UserInDB, UserCreate, UserResponse, AuthResponse
from middleware.auth import get_current_active_user
from core.security import get_password_hash
from bson.objectid import ObjectId

logger = logging.getLogger(__name__)
router = APIRouter(tags=["auth"])
@router.post("/token", response_model=AuthResponse, summary="Login to get access token")
@router.post("/token", response_model=AuthResponse, summary="Login to get access token")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    """
    OAuth2 compatible token login, get an access token for future requests
    """
    try:
        logger.info(f"Login attempt for user: {form_data.username}")
        
        # Check if user exists
        user_dict = await db["users"].find_one({"email": form_data.username})
        if not user_dict:
            logger.warning(f"Login failed: User not found - {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )
        # Convert ObjectId to string
        user_dict["id"] = str(user_dict.pop("_id"))

        # Convert ObjectId to string
        user_dict["id"] = str(user_dict.pop("_id"))
        user = UserInDB(**user_dict)
        
        # Verify password
        if not verify_password(form_data.password, user.password):
            logger.warning(f"Login failed: Invalid password for user - {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )
            {"_id": ObjectId(user.id)},
        # Update last login
        await db["users"].update_one(
            {"_id": ObjectId(user.id)},
            {"$set": {"last_login": datetime.utcnow()}}
        )
        
        # Create UserResponse object
        user_response = UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
            last_login=user.last_login,
            preferences=user.preferences
        )
        
        logger.info(f"Login successful for user: {user.email}")
        return AuthResponse(
            access_token=access_token,
            token_type="bearer",
            user=user_response
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
@router.post("/register", response_model=AuthResponse, summary="Register a new user")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )

@router.post("/register", response_model=AuthResponse, summary="Register a new user")
async def register(
    user_data: UserCreate,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    """Register a new user"""
    try:
        logger.info(f"Registration attempt for email: {user_data.email}")
        
        # Check if user already exists
        existing_user = await db["users"].find_one({"email": user_data.email})
        if existing_user:
            logger.warning(f"Registration failed: Email already exists - {user_data.email}")
            raise HTTPException(
                status_code=400,
                detail="Email already registered"
            )

        # Hash the password
        hashed_password = get_password_hash(user_data.password)

        # Create user document
        user_dict = user_data.dict()
        user_dict["password"] = hashed_password
        user_dict["created_at"] = datetime.utcnow()
        user_dict["role"] = "user"
        user_dict["is_active"] = True
        user_dict["preferences"] = {}
        user_dict["last_login"] = None

        # Insert into database
        try:
            result = await db["users"].insert_one(user_dict)
            user_dict["id"] = str(result.inserted_id)
        except Exception as db_error:
            logger.error(f"Database error during user creation: {str(db_error)}")
            raise HTTPException(
                status_code=500,
                detail="Failed to create user account"

        access_token = create_access_token(
            data={"sub": user_data.email}
            id=user_dict["id"],

        # Create UserResponse object
        user_response = UserResponse(
            id=user_dict["id"],
            email=user_dict["email"],
            name=user_dict["name"],
            role=user_dict["role"],
            is_active=user_dict["is_active"],
            created_at=user_dict["created_at"],
        logger.info(f"Registration successful for user: {user_data.email}")
        
        # Return AuthResponse
        return AuthResponse(
            access_token=access_token,
            token_type="bearer",
            user=user_response
        )
        # Return AuthResponse
        return AuthResponse(
            access_token=access_token,
            token_type="bearer",
            user=user_response
        )

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Unexpected error during registration: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Registration failed: {str(e)}"
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
