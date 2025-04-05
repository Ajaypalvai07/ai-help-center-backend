from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from core.config import settings
from models.user import UserInDB, User
from core.database import get_db_dependency
from core.auth import decode_token
from motor.motor_asyncio import AsyncIOMotorDatabase
import logging

logger = logging.getLogger(__name__)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

async def get_current_user(
    token: str = Depends(oauth2_scheme), 
    db: AsyncIOMotorDatabase = Depends(get_db_dependency)
) -> UserInDB:
    """Verify JWT token and return user."""
    try:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
        # Decode the token
        payload = decode_token(token)
        if not payload:
            logger.error("Token decode failed")
            raise credentials_exception

        if "sub" not in payload:
            logger.error("Token payload missing 'sub' claim")
            raise credentials_exception

        email = payload["sub"]
        logger.debug(f"Looking up user with email: {email}")
        
        # Get user from database
        user = await db.users.find_one({"email": email})
        if not user:
            logger.error(f"User not found: {email}")
            raise credentials_exception
        
        # Convert MongoDB ObjectId to string and rename _id to id
        user["id"] = str(user.pop("_id"))
        
        # Ensure password field exists
        if "password" not in user:
            logger.error(f"User {email} missing password field")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User data corrupted"
            )
        
        # Create and return UserInDB instance
        try:
            return UserInDB(**user)
        except Exception as e:
            logger.error(f"Error creating UserInDB instance: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error processing user data"
            )
            
    except JWTError as e:
        logger.error(f"JWT validation error: {str(e)}")
        raise credentials_exception
    except Exception as e:
        logger.error(f"Unexpected error in get_current_user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

async def get_current_active_user(
    current_user: UserInDB = Depends(get_current_user)
) -> UserInDB:
    """Ensure user is active."""
    if not current_user.is_active:
        logger.warning(f"Inactive user attempted access: {current_user.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )
    return current_user

async def get_current_admin(
    current_user: UserInDB = Depends(get_current_active_user)
) -> UserInDB:
    """Ensure user is an admin."""
    if current_user.role != "admin":
        logger.warning(f"Non-admin user attempted admin access: {current_user.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user
