from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import datetime
from core.database import get_db_dependency
from core.auth import verify_password, get_password_hash, create_access_token
from models.user import UserCreate, UserResponse, UserInDB, User
from middleware.auth import get_current_user, get_current_active_user
from motor.motor_asyncio import AsyncIOMotorDatabase

router = APIRouter(tags=["auth"])

@router.post("/token", summary="Login to get access token")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    """Authenticate user and return access token."""
    try:
        print(f"Login attempt for username: {form_data.username}")
        
        user = await db.users.find_one({"email": form_data.username})
        if not user:
            print(f"User not found with email: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Incorrect email or password"
            )

        if not verify_password(form_data.password, user["password"]):
            print(f"Invalid password for user: {form_data.username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Incorrect email or password"
            )

        print(f"Successful login for user: {form_data.username}")
        
        # Update last login timestamp
        await db.users.update_one(
            {"_id": user["_id"]}, 
            {"$set": {"last_login": datetime.utcnow()}}
        )
        
        access_token = create_access_token(data={"sub": user["email"]})

        # Convert to UserResponse
        user_response = UserResponse(
            id=str(user["_id"]),
            email=user["email"],
            name=user["name"],
            role=user["role"],
            is_active=user["is_active"],
            created_at=user["created_at"],
            last_login=user["last_login"],
            preferences=user.get("preferences", {})
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user_response
        }
    except Exception as e:
        print(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/register", response_model=User, summary="Register a new user")
async def register(
    user_data: UserCreate,
    db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    """Register a new user."""
    try:
        # Check if user already exists
        existing_user = await db.users.find_one({"email": user_data.email})
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Create user dictionary
        user_dict = {
            "email": user_data.email,
            "name": user_data.name,
            "password": get_password_hash(user_data.password),
            "created_at": datetime.utcnow(),
            "last_login": None,
            "preferences": {},
            "role": "user",
            "is_active": True
        }

        # Insert the new user
        result = await db.users.insert_one(user_dict)
        if not result.inserted_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user"
            )

        # Retrieve the created user
        created_user = await db.users.find_one({"_id": result.inserted_id})
        if not created_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User created but could not be retrieved"
            )

        # Convert MongoDB _id to string
        created_user["id"] = str(created_user.pop("_id"))
        
        # Create access token for the new user
        access_token = create_access_token(data={"sub": created_user["email"]})
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": User(**created_user)
        }

    except HTTPException as he:
        # Re-raise HTTP exceptions
        raise he
    except Exception as e:
        print(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@router.get("/verify", response_model=UserResponse, summary="Verify current token")
async def verify_token(
    current_user: UserInDB = Depends(get_current_active_user),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency)
):
    """Verify current user's token."""
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
        print(f"Error in verify_token: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to verify token"
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
