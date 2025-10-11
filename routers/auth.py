from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Form, Header, Depends
from fastapi.responses import JSONResponse
from uuid import uuid4
from datetime import datetime, timedelta
from utils.database import read_users, write_users
from core.config import IST, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, SECRET_KEY, ALGORITHM
from core.security import hash_password, verify_password, create_access_token
from core.rate_limiting import auth_rate_limit, api_rate_limit
from core.jwt_security import jwt_security_manager
from middleware.jwt_auth import get_current_user_id
from models.validation import SecureUserRegister, SecureUserLogin, SecureUserUpdate
from models.user import User
from utils.input_validator import input_validator
from utils.structured_logging import log_user_registration, track_error
from utils.security import sql_protection
from services.notification_service import send_welcome_notification
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
import os
import shutil
import logging
from pathlib import Path
from jose import jwt

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])

# OAuth Config
config = Config(environ=os.environ)
oauth = OAuth(config)
oauth.register(
    name="google",
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

def _load_users():
    return read_users()

def _save_users(data):
    write_users(data)

@router.post("/register")
@auth_rate_limit("register")
async def register(user_register: SecureUserRegister, request: Request):
    try:
        # Validate and sanitize input
        user_register.name = input_validator.sanitize_name(user_register.name)
        user_register.email = input_validator.sanitize_email(user_register.email)
        user_register.phone = input_validator.sanitize_phone(user_register.phone)

        users = _load_users()

        # Check if phone number already exists
        existing_phone = next((u for u in users if u["phone"] == user_register.phone), None)
        if existing_phone:
            from utils.error_responses import create_field_validation_error
            error = create_field_validation_error(
                field="phone",
                message="Phone number already registered",
                code="PHONE_ALREADY_REGISTERED",
                user_message="This phone number is already registered. Please use a different number or try logging in."
            )
            raise error

        # Check if email already exists
        existing_email = next((u for u in users if u.get("email") == user_register.email), None)
        if existing_email:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "EMAIL_ALREADY_REGISTERED",
                    "message": "Email already registered.",
                    "code": "AUTH_006",
                    "timestamp": datetime.now(IST).isoformat()
                }
            )

        # Create new user with hashed password
        hashed_password = hash_password(user_register.password)
        new_user = User(
            id="u_" + uuid4().hex[:10],
            name=user_register.name,
            phone=user_register.phone,
            email=user_register.email,
            password=hashed_password,
            role="user",
            createdAt=datetime.now(IST).isoformat()
        ).dict()
        users.append(new_user)
        _save_users(users)

        # Create access token using enhanced JWT security
        access_token = jwt_security_manager.create_token(new_user["id"], {"role": new_user.get("role", "user")})

        # Log user registration
        log_user_registration(new_user["id"], "email", request)

        # Send welcome notification
        try:
            send_welcome_notification(new_user["id"], new_user["name"])
        except Exception as e:
            # Don't fail registration if notification fails
            pass

        return {
            "msg": "User registered successfully",
            "user": {
                "id": new_user["id"],
                "name": new_user["name"],
                "email": new_user["email"],
                "phone": new_user["phone"],
                "createdAt": new_user["createdAt"]
            },
            "access_token": access_token,
            "token_type": "bearer"
        }
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": "REGISTRATION_FAILED",
                "message": "Failed to complete user registration.",
                "code": "AUTH_004",
                "timestamp": datetime.now(IST).isoformat(),
                "details": str(e) if os.getenv("DEBUG", "false").lower() == "true" else None
            }
        )

@router.post("/login")
@auth_rate_limit("login")
async def login(user_login: SecureUserLogin, request: Request):
    try:


        users = _load_users()

        # Find user by phone number
        user = next((u for u in users if u["phone"] == user_login.phone), None)
        if not user:
            return JSONResponse(
                status_code=401,
                content={
                    "error": {
                        "type": "USER_NOT_FOUND",
                        "message": "User not found. Please register first.",
                        "code": "AUTH_001",
                        "timestamp": datetime.now(IST).isoformat()
                    }
                }
            )

        # Check if user has a password (registered users should have one)
        if not user.get("password"):
            return JSONResponse(
                status_code=401,
                content={
                    "error": {
                        "type": "USER_HAS_NO_PASSWORD",
                        "message": "User found but has no password. Please complete registration with password.",
                        "code": "AUTH_002",
                        "timestamp": datetime.now(IST).isoformat()
                    }
                }
            )

        # Verify password
        if not verify_password(user_login.password, user["password"]):
            return JSONResponse(
                status_code=401,
                content={
                    "error": {
                        "type": "INVALID_PASSWORD",
                        "message": "Invalid password provided.",
                        "code": "AUTH_003",
                        "timestamp": datetime.now(IST).isoformat()
                    }
                }
            )

        # Create access token using enhanced JWT security
        access_token = jwt_security_manager.create_token(user["id"], {"role": user.get("role", "user")})

        return {
            "msg": "login_successful",
            "user": {
                "id": user["id"],
                "name": user["name"],
                "email": user.get("email"),
                "phone": user["phone"],
                "bio": user.get("bio"),
                "strava_link": user.get("strava_link"),
                "instagram_id": user.get("instagram_id"),
                "picture": user.get("picture"),
                "role": user.get("role", "user"),
                "createdAt": user["createdAt"]
            },
            "access_token": access_token,
            "token_type": "bearer"
        }
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "type": "INTERNAL_ERROR",
                    "message": "Internal server error during login.",
                    "code": "AUTH_999",
                    "timestamp": datetime.now(IST).isoformat(),
                    "details": str(e) if os.getenv("DEBUG", "false").lower() == "true" else None
                }
            }
        )

@router.get("/me")
@api_rate_limit("profile")
async def get_current_user_profile(request: Request, current_user_id: str = Depends(get_current_user_id)):
    """Get current user profile (secure endpoint)"""
    try:
        users = _load_users()
        user = next((u for u in users if u["id"] == current_user_id), None)
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return {
            "id": user["id"],
            "name": user["name"],
            "email": user.get("email"),
            "phone": user.get("phone"),
            "role": user.get("role", "user"),
            "bio": user.get("bio"),
            "picture": user.get("picture"),
            "strava_link": user.get("strava_link"),
            "instagram_id": user.get("instagram_id"),
            "is_private": user.get("is_private", False),
            "createdAt": user["createdAt"]
        }
    except HTTPException:
        raise
    except Exception as e:
        track_error("profile_fetch_failed", str(e), request=request)
        raise HTTPException(status_code=500, detail=f"Failed to fetch profile: {str(e)}")

@router.get("/admin/users")
@api_rate_limit("admin")
async def get_users_admin(request: Request, current_user_id: str = Depends(get_current_user_id)):
    """Get users list for admin (secure endpoint with role check)"""
    try:
        # Check if user is admin
        users = _load_users()
        current_user = next((u for u in users if u["id"] == current_user_id), None)
        if not current_user or current_user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Return only safe user data for admin
        safe_users = []
        for user in users:
            safe_users.append({
                "id": user["id"],
                "name": user["name"],
                "email": user.get("email"),
                "phone": user.get("phone"),
                "role": user.get("role", "user"),
                "createdAt": user["createdAt"],
                "is_private": user.get("is_private", False)
            })
        
        return {
            "users": safe_users,
            "total": len(safe_users)
        }
    except HTTPException:
        raise
    except Exception as e:
        track_error("admin_users_fetch_failed", str(e), request=request)
        raise HTTPException(status_code=500, detail=f"Failed to fetch users: {str(e)}")

@router.get("/user/{phone}")
async def get_user_by_phone(phone: str):
    users = _load_users()
    user = next((u for u in users if u["phone"] == phone), None)
    if not user:
        return JSONResponse(
            status_code=404,
            content={
                "error": "USER_NOT_FOUND",
                "message": "User not found.",
                "code": "AUTH_007",
                "timestamp": datetime.now(IST).isoformat()
            }
        )
    return user

@router.put("/user/{user_id}")
@api_rate_limit("authenticated")
async def update_user(
    user_id: str,
    name: str = Form(None),
    phone: str = Form(None),
    email: str = Form(None),
    bio: str = Form(None),
    strava_link: str = Form(None),
    instagram_id: str = Form(None),
    picture: UploadFile = File(None),
    request: Request = None,
    current_user_id: str = Depends(get_current_user_id)
):
    # Security check - users can only update their own profile
    if current_user_id != user_id:
        return JSONResponse(
            status_code=403,
            content={
                "error": "FORBIDDEN_UPDATE",
                "message": "Can only update your own profile.",
                "code": "AUTH_008",
                "timestamp": datetime.now(IST).isoformat()
            }
        )
    
    users = _load_users()
    user = next((u for u in users if u["id"] == user_id), None)
    if not user:
        return JSONResponse(
            status_code=404,
            content={
                "error": "USER_NOT_FOUND",
                "message": "User not found.",
                "code": "AUTH_009",
                "timestamp": datetime.now(IST).isoformat()
            }
        )

    # Sanitize input data
    update_data = {
        "name": name,
        "phone": phone,
        "email": email,
        "bio": bio,
        "strava_link": strava_link,
        "instagram_id": instagram_id
    }
    sanitized_data = sql_protection.validate_input(update_data)

    # Update only provided fields
    updated = False

    if sanitized_data["name"] is not None and sanitized_data["name"].strip():
        user["name"] = sanitized_data["name"].strip()
        updated = True

    if sanitized_data["phone"] is not None and sanitized_data["phone"].strip():
        new_phone = sanitized_data["phone"].strip()
        # Validate phone format
        if not input_validator.validate_phone_number(new_phone):
            return JSONResponse(
                status_code=400,
                content={
                    "error": "INVALID_PHONE_FORMAT",
                    "message": "Invalid phone number format.",
                    "code": "AUTH_010",
                    "timestamp": datetime.now(IST).isoformat()
                }
            )
        # Check if phone number already exists for another user
        existing_phone_user = next((u for u in users if u["phone"] == new_phone and u["id"] != user_id), None)
        if existing_phone_user:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "PHONE_ALREADY_IN_USE",
                    "message": "Phone number already exists for another user.",
                    "code": "AUTH_011",
                    "timestamp": datetime.now(IST).isoformat()
                }
            )
        user["phone"] = new_phone
        updated = True

    if sanitized_data["email"] is not None and sanitized_data["email"].strip():
        email = sanitized_data["email"].strip()
        # Validate email format
        if not input_validator.validate_email(email):
            return JSONResponse(
                status_code=400,
                content={
                    "error": "INVALID_EMAIL_FORMAT",
                    "message": "Invalid email format.",
                    "code": "AUTH_012",
                    "timestamp": datetime.now(IST).isoformat()
                }
            )
        user["email"] = email
        updated = True

    if sanitized_data["bio"] is not None:
        user["bio"] = sanitized_data["bio"].strip() if sanitized_data["bio"].strip() else None
        updated = True

    if sanitized_data["strava_link"] is not None:
        strava_link = sanitized_data["strava_link"].strip() if sanitized_data["strava_link"].strip() else None
        if strava_link and not input_validator.validate_url(strava_link):
            return JSONResponse(
                status_code=400,
                content={
                    "error": "INVALID_STRAVA_LINK_FORMAT",
                    "message": "Invalid Strava link format.",
                    "code": "AUTH_013",
                    "timestamp": datetime.now(IST).isoformat()
                }
            )
        user["strava_link"] = strava_link
        updated = True

    if sanitized_data["instagram_id"] is not None:
        user["instagram_id"] = sanitized_data["instagram_id"].strip() if sanitized_data["instagram_id"].strip() else None
        updated = True

    if picture is not None:
        try:
            # Use comprehensive file security validation
            from utils.file_security import validate_profile_image

            logger.info(f"Starting profile picture upload for user {user_id}")

            # Validate the uploaded file using comprehensive security checks
            validation_result = validate_profile_image(picture)

            logger.info(f"File validation passed for user {user_id}: {validation_result['filename']} ({validation_result['file_size']} bytes)")

            # Create uploads directory if it doesn't exist
            upload_dir = Path("uploads/profiles")
            try:
                upload_dir.mkdir(parents=True, exist_ok=True)
                logger.info(f"Upload directory ready: {upload_dir}")
            except Exception as dir_error:
                logger.error(f"Failed to create upload directory for user {user_id}: {dir_error}")
                return JSONResponse(
                    status_code=500,
                    content={
                        "error": "UPLOAD_DIR_ERROR",
                        "message": "Failed to create upload directory.",
                        "code": "AUTH_020",
                        "timestamp": datetime.now(IST).isoformat()
                    }
                )

            # Generate secure filename
            unique_filename = f"{user_id}_{uuid4().hex[:8]}{validation_result['extension']}"
            file_path = upload_dir / unique_filename

            logger.info(f"Attempting to save file for user {user_id}: {file_path}")

            # Atomic file operation with rollback capability
            temp_file_path = None
            try:
                # Create temporary file for atomic operation
                import tempfile
                import os

                # Create temporary file in the same directory to ensure atomic move
                temp_fd, temp_file_path = tempfile.mkstemp(suffix=validation_result['extension'], dir=upload_dir)
                temp_file = os.fdopen(temp_fd, 'wb')

                # Write file content in chunks
                bytes_written = 0
                chunk = picture.file.read(8192)  # Read in 8KB chunks
                while chunk:
                    temp_file.write(chunk)
                    bytes_written += len(chunk)
                    chunk = picture.file.read(8192)

                temp_file.close()

                logger.info(f"Successfully wrote temp file for user {user_id}: {bytes_written} bytes")

                # Verify temporary file was written correctly
                if not os.path.exists(temp_file_path) or os.path.getsize(temp_file_path) == 0:
                    logger.error(f"Temp file verification failed for user {user_id}")
                    # Clean up temp file
                    if temp_file_path and os.path.exists(temp_file_path):
                        os.unlink(temp_file_path)
                    return JSONResponse(
                        status_code=500,
                        content={
                            "error": "FILE_SAVE_ERROR",
                            "message": "Failed to save file to disk.",
                            "code": "AUTH_021",
                            "timestamp": datetime.now(IST).isoformat()
                        }
                    )

                # Atomic move from temp file to final location
                final_file_path = upload_dir / unique_filename
                os.rename(temp_file_path, final_file_path)

                # Verify final file exists and has correct size
                if not final_file_path.exists() or final_file_path.stat().st_size != bytes_written:
                    logger.error(f"Final file verification failed for user {user_id}")
                    # Clean up final file if it exists
                    if final_file_path.exists():
                        os.unlink(final_file_path)
                    return JSONResponse(
                        status_code=500,
                        content={
                            "error": "FILE_FINALIZE_ERROR",
                            "message": "Failed to finalize file save operation.",
                            "code": "AUTH_024",
                            "timestamp": datetime.now(IST).isoformat()
                        }
                    )

                # Optimize the uploaded image
                from utils.file_security import optimize_image
                from pathlib import Path

                image_path = Path(f"uploads/profiles/{unique_filename}")
                try:
                    optimized_path = optimize_image(image_path, max_size=(800, 800), quality=85)
                    logger.info(f"Image optimization completed for {unique_filename}")
                except Exception as opt_error:
                    logger.warning(f"Image optimization failed for {unique_filename}: {opt_error}")
                    # Continue with original file if optimization fails

                # Store the relative path in user record
                user["picture"] = f"/uploads/profiles/{unique_filename}"
                updated = True

                logger.info(f"Profile picture updated successfully for user {user_id}: {unique_filename}")

            except Exception as file_error:
                logger.error(f"Failed to save file for user {user_id}: {file_error}")
                # Clean up temp file if it exists
                if temp_file_path and os.path.exists(temp_file_path):
                    try:
                        os.unlink(temp_file_path)
                    except:
                        pass
                return JSONResponse(
                    status_code=500,
                    content={
                        "error": "FILE_WRITE_ERROR",
                        "message": "Failed to write file to disk.",
                        "code": "AUTH_022",
                        "timestamp": datetime.now(IST).isoformat()
                    }
                )

        except HTTPException as http_error:
            # Re-raise HTTP exceptions (validation errors)
            logger.error(f"File validation failed for user {user_id}: {http_error.detail}")
            raise
        except Exception as upload_error:
            logger.error(f"Unexpected error during file upload for user {user_id}: {upload_error}")
            return JSONResponse(
                status_code=500,
                content={
                    "error": "UPLOAD_ERROR",
                    "message": "Unexpected error during file upload.",
                    "code": "AUTH_023",
                    "timestamp": datetime.now(IST).isoformat()
                }
            )

    if not updated:
        return JSONResponse(
            status_code=400,
            content={
                "error": "NO_FIELDS_TO_UPDATE",
                "message": "No fields provided for update.",
                "code": "AUTH_014",
                "timestamp": datetime.now(IST).isoformat()
            }
        )

    # Save updated users
    _save_users(users)
    return {"msg": "User updated successfully", "user": user}

@router.get("/password")
async def return_password():
    return "yesmakeedits"

# Google OAuth routes
@router.get("/google_login")
@auth_rate_limit("google_auth")
async def google_login(request: Request):
    redirect_uri = request.url_for("google_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/google_login/callback")
async def google_callback(request: Request):
    try:
        token = await oauth.google.authorize_access_token(request)
        user_info = token.get("userinfo")

        if not user_info:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "GOOGLE_LOGIN_FAILED",
                    "message": "Google login failed.",
                    "code": "AUTH_015",
                    "timestamp": datetime.now(IST).isoformat()
                }
            )

        users = _load_users()
        # Check if user exists by email
        existing_user = next((u for u in users if u.get("email") == user_info["email"]), None)

        if existing_user:
            # User exists, return existing user info
            access_token = jwt_security_manager.create_token(existing_user["id"], {"role": existing_user.get("role", "user")})
            return {
                "msg": "login_successful",
                "user": {
                    "id": existing_user["id"],
                    "name": existing_user["name"],
                    "email": existing_user.get("email"),
                    "picture": existing_user.get("picture"),
                    "phone": existing_user.get("phone"),
                    "bio": existing_user.get("bio"),
                    "strava_link": existing_user.get("strava_link"),
                    "instagram_id": existing_user.get("instagram_id"),
                    "role": existing_user.get("role", "user"),
                    "createdAt": existing_user["createdAt"]
                },
                "access_token": access_token,
                "token_type": "bearer"
            }

        # User doesn't exist, create new user
        new_user = User(
            id="u_" + uuid4().hex[:10],
            name=user_info.get("name"),
            email=user_info["email"],
            picture=user_info.get("picture"),
            google_id=user_info.get("sub"),
            role="user",
            createdAt=datetime.now(IST).isoformat()
        ).dict()
        users.append(new_user)
        _save_users(users)
        access_token = jwt_security_manager.create_token(new_user["id"], {"role": "user"})
        return {
            "msg": "registered",
            "user": {
                "id": new_user["id"],
                "name": new_user["name"],
                "email": new_user["email"],
                "picture": new_user["picture"],
                "bio": new_user.get("bio"),
                "strava_link": new_user.get("strava_link"),
                "instagram_id": new_user.get("instagram_id"),
                "role": new_user.get("role", "user"),
                "createdAt": new_user["createdAt"]
            },
            "access_token": access_token,
            "token_type": "bearer"
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": "GOOGLE_LOGIN_ERROR",
                "message": "Google login failed.",
                "code": "AUTH_016",
                "timestamp": datetime.now(IST).isoformat(),
                "details": str(e) if os.getenv("DEBUG", "false").lower() == "true" else None
            }
        )

@router.get("/points")
@api_rate_limit("authenticated")
async def get_user_points(request: Request, current_user_id: str = Depends(get_current_user_id)):
    """Get user points for display"""
    from utils.database import get_user_points

    points_data = get_user_points(current_user_id)

    # Return user-friendly format
    return {
        "user_id": points_data["id"],
        "total_points": points_data["total_points"],
        "point_history": points_data["transaction_history"]
    }

@router.post("/test-upload")
@api_rate_limit("authenticated")
async def test_file_upload(
    request: Request,
    picture: UploadFile = File(...),
    current_user_id: str = Depends(get_current_user_id)
):
    """Test endpoint to verify file upload functionality"""
    try:
        logger.info(f"Test upload initiated for user {current_user_id}")

        # Use comprehensive file security validation
        from utils.file_security import validate_profile_image

        # Validate the uploaded file using comprehensive security checks
        validation_result = validate_profile_image(picture)

        logger.info(f"File validation passed for user {current_user_id}: {validation_result['filename']} ({validation_result['file_size']} bytes)")

        # Create uploads directory if it doesn't exist
        upload_dir = Path("uploads/profiles")
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Generate test filename
        test_filename = f"test_{current_user_id}_{uuid4().hex[:8]}{validation_result['extension']}"
        file_path = upload_dir / test_filename

        # Atomic file operation with rollback capability
        temp_file_path = None
        try:
            # Create temporary file for atomic operation
            import tempfile
            import os

            # Create temporary file in the same directory to ensure atomic move
            temp_fd, temp_file_path = tempfile.mkstemp(suffix=validation_result['extension'], dir=upload_dir)
            temp_file = os.fdopen(temp_fd, 'wb')

            # Write file content in chunks
            bytes_written = 0
            chunk = picture.file.read(8192)  # Read in 8KB chunks
            while chunk:
                temp_file.write(chunk)
                bytes_written += len(chunk)
                chunk = picture.file.read(8192)

            temp_file.close()

            logger.info(f"Successfully wrote temp file for user {current_user_id}: {bytes_written} bytes")

            # Atomic move from temp file to final location
            final_file_path = upload_dir / test_filename
            os.rename(temp_file_path, final_file_path)

            # Optimize the uploaded image
            from utils.file_security import optimize_image

            try:
                optimized_path = optimize_image(final_file_path, max_size=(800, 800), quality=85)
                logger.info(f"Image optimization completed for test file {test_filename}")
            except Exception as opt_error:
                logger.warning(f"Image optimization failed for test file {test_filename}: {opt_error}")

            # Verify file was written and optimized
            if final_file_path.exists() and final_file_path.stat().st_size > 0:
                logger.info(f"Test upload successful: {test_filename}")

                return {
                    "success": True,
                    "message": "File upload test successful",
                    "filename": test_filename,
                    "file_size": validation_result['file_size'],
                    "bytes_written": bytes_written,
                    "file_path": str(final_file_path),
                    "mime_type": validation_result['mime_type'],
                    "verification": "File exists and has content",
                    "optimization": "Applied" if Image else "Skipped (PIL not available)"
                }
            else:
                logger.error(f"Test upload failed verification: {test_filename}")
                return JSONResponse(
                    status_code=500,
                    content={
                        "success": False,
                        "error": "File verification failed",
                        "file_path": str(final_file_path)
                    }
                )

        except Exception as file_error:
            logger.error(f"Failed to save test file for user {current_user_id}: {file_error}")
            # Clean up temp file if it exists
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": f"File save error: {str(file_error)}"
                }
            )

    except HTTPException as http_error:
        # Re-raise HTTP exceptions (validation errors)
        logger.error(f"File validation failed for user {current_user_id}: {http_error.detail}")
        raise
    except Exception as e:
        logger.error(f"Test upload error for user {current_user_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )

@router.post("/admin/cleanup-uploads")
@api_rate_limit("admin")
async def cleanup_uploads(
    request: Request,
    max_age_hours: int = 24,
    current_user_id: str = Depends(get_current_user_id)
):
    """Admin endpoint to clean up old upload files"""
    try:
        # Check if user is admin
        users = _load_users()
        current_user = next((u for u in users if u["id"] == current_user_id), None)
        if not current_user or current_user.get("role") != "admin":
            raise HTTPException(status_code=403, detail="Admin access required")

        from utils.file_security import cleanup_failed_uploads
        from pathlib import Path

        upload_dir = Path("uploads/profiles")
        cleanup_failed_uploads(upload_dir, max_age_hours)

        return {
            "success": True,
            "message": f"Upload cleanup completed for files older than {max_age_hours} hours",
            "directory": str(upload_dir),
            "timestamp": datetime.now(IST).isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload cleanup failed: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Cleanup failed: {str(e)}"
            }
        )

@router.delete("/user/{user_id}")
@api_rate_limit("authenticated")
async def delete_user_profile(
    user_id: str,
    request: Request,
    current_user_id: str = Depends(get_current_user_id)
):
    """Delete user profile (users can delete their own profile, admins can delete any profile)"""
    try:
        users = _load_users()

        # Find the user to be deleted
        user_to_delete = next((u for u in users if u["id"] == user_id), None)
        if not user_to_delete:
            return JSONResponse(
                status_code=404,
                content={
                    "error": "USER_NOT_FOUND",
                    "message": "User not found.",
                    "code": "AUTH_017",
                    "timestamp": datetime.now(IST).isoformat()
                }
            )

        # Find the current user (for authorization check)
        current_user = next((u for u in users if u["id"] == current_user_id), None)
        if not current_user:
            raise HTTPException(status_code=404, detail="Current user not found")

        # Authorization check: users can delete their own profile, admins can delete any profile
        if current_user_id != user_id and current_user.get("role") != "admin":
            return JSONResponse(
                status_code=403,
                content={
                    "error": "FORBIDDEN_DELETE",
                    "message": "Can only delete your own profile or must be admin to delete other profiles.",
                    "code": "AUTH_018",
                    "timestamp": datetime.now(IST).isoformat()
                }
            )

        # Prevent admin from deleting themselves (safety measure)
        if current_user_id == user_id and current_user.get("role") == "admin":
            return JSONResponse(
                status_code=400,
                content={
                    "error": "ADMIN_SELF_DELETE_NOT_ALLOWED",
                    "message": "Admin users cannot delete their own profiles. Contact another admin.",
                    "code": "AUTH_019",
                    "timestamp": datetime.now(IST).isoformat()
                }
            )

        # Clean up profile picture if it exists
        if user_to_delete.get("picture"):
            try:
                picture_path = user_to_delete["picture"]
                # Remove leading slash if present
                if picture_path.startswith("/"):
                    picture_path = picture_path[1:]

                file_path = Path(picture_path)
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"Deleted profile picture for user {user_id}: {picture_path}")
            except Exception as file_error:
                logger.warning(f"Failed to delete profile picture for user {user_id}: {file_error}")
                # Continue with user deletion even if file cleanup fails

        # Remove user from the users list
        users = [u for u in users if u["id"] != user_id]

        # Save updated users list
        _save_users(users)

        # Log the deletion
        log_user_registration(user_id, "user_deleted", request)

        return {
            "msg": "User profile deleted successfully",
            "deleted_user_id": user_id,
            "deleted_at": datetime.now(IST).isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        track_error("user_deletion_failed", str(e), request=request)
        logger.error(f"User deletion failed for user {user_id}: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "USER_DELETION_FAILED",
                "message": "Failed to delete user profile.",
                "code": "AUTH_020",
                "timestamp": datetime.now(IST).isoformat(),
                "details": str(e) if os.getenv("DEBUG", "false").lower() == "true" else None
            }
        )
