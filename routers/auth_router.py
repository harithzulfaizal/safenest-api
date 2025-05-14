from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordRequestForm

import models 
import services 
from database import get_supabase_client 
# import config 

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"] 
)

@router.post("/register_login",
             response_model=models.UserLoginResponse,
             status_code=status.HTTP_201_CREATED,
             summary="Register Login Credentials for a User (Hashed Password)",
             description="Creates a new login entry (email and password) for an *existing* user. "
                         "The user profile (with user_id) must already exist in the 'users' table. "
                         "The provided password will be securely hashed before being stored in the 'password_hash' column of the 'user_logins' table.")
async def register_login_credentials_route(
    login_details: models.UserLoginCreate = Body(..., description="User ID, email, and password for the new login entry. Password will be hashed."),
    supabase: Any = Depends(get_supabase_client) 
):
    """
    Endpoint to register login credentials for an existing user with password hashing.
    - **user_id**: The ID of the user (must exist in the `users` table).
    - **email**: The email address for login (must be unique in `user_logins`).
    - **password**: The password for the user (will be securely hashed).
    """
    try:
        created_login_record = await services.register_user_login(login_data=login_details, supabase=supabase)
        return created_login_record
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        print(f"Unexpected error in POST /auth/register_login route: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected server error occurred while registering login credentials: {str(e)}"
        )

@router.post("/login", 
             response_model=models.UserLoginSuccessResponse, # Using the simple success response
             summary="User Login (Simple)",
             description="Authenticates a user based on email and password. "
                         "If successful, returns user details. Does NOT return a JWT token in this simple version.")
async def simple_login_route(
    # Using Pydantic model for JSON body instead of form data for this simple version
    form_data: models.UserLoginRequest = Body(..., description="User's email and password for login."),
    supabase: Any = Depends(get_supabase_client)
):
    """
    Simple login endpoint.
    Takes email and password in a JSON body.
    Verifies credentials against the stored hashed password.
    Updates `last_login` timestamp on successful authentication.
    """
    print(f"Login attempt for email: {form_data.email}")
    
    authenticated_user_login_details = await services.simple_authenticate_user(
        email=form_data.email, 
        password=form_data.password, 
        supabase=supabase
    )
    
    if not authenticated_user_login_details:
        print(f"Login failed for email: {form_data.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    print(f"Login successful for email: {form_data.email}, user_id: {authenticated_user_login_details.user_id}")
    
    return models.UserLoginSuccessResponse(
        user_id=authenticated_user_login_details.user_id,
        email=authenticated_user_login_details.email,
        message=f"Login successful for user_id {authenticated_user_login_details.user_id}."
    )

# @router.post("/token", response_model=models.Token, summary="User Login for Access Token (JWT)")
# async def login_for_access_token(
#     form_data: OAuth2PasswordRequestForm = Depends(), 
#     supabase: Any = Depends(get_supabase_client)
# ):
#     """
#     Standard OAuth2 password flow for obtaining a JWT access token.
#     'username' field from the form is treated as the email.
#     """
#     user = await services.authenticate_user( 
#         email=form_data.username, 
#         password=form_data.password,
#         supabase=supabase
#     )
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Incorrect email or password",
#             headers={"WWW-Authenticate": "Bearer"},
#         )
#     access_token_expires = timedelta(minutes=config.ACCESS_TOKEN_EXPIRE_MINUTES)
#     access_token_payload = {
#         "sub": user.email, 
#         "user_id": user.user_id, 
#     }
#     access_token = services.create_access_token(
#         data=access_token_payload, expires_delta=access_token_expires
#     )
#     return {"access_token": access_token, "token_type": "bearer"}
