"""
Admin Routes
Provides administrative functionality for managing users, events, and system operations
"""
from fastapi import APIRouter, HTTPException, Depends, Request, Query
from fastapi.responses import JSONResponse
from uuid import uuid4
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from core.rate_limiting import api_rate_limit
from core.rbac import require_role, UserRole, require_authenticated, get_current_user_id
from utils.security import sql_protection
from utils.structured_logging import track_error
from core.exceptions import (
    ValidationError,
    BusinessLogicError,
    DatabaseError,
    handle_database_error
)
from utils.database import (
    read_users, read_events, get_user_points, deduct_points_from_user,
    award_points_to_user, read_user_points
)
from core.config import IST
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])

# Pydantic Models for Admin Operations
class PointDeductionRequest(BaseModel):
    user_id: str = Field(..., min_length=1, description="User ID from QR code")
    points: int = Field(..., gt=0, le=10000, description="Number of points to deduct")
    reason: str = Field(..., min_length=1, max_length=200, description="Reason for point deduction")

class PointAwardRequest(BaseModel):
    user_id: str = Field(..., min_length=1, description="User ID")
    points: int = Field(..., gt=0, le=10000, description="Number of points to award")
    reason: str = Field(..., min_length=1, max_length=200, description="Reason for awarding points")

class UserPointsResponse(BaseModel):
    user_id: str
    current_points: int
    transaction_history: List[Dict[str, Any]]

@router.post("/deduct-points", response_model=Dict[str, Any])
@require_role(UserRole.ADMIN)
@api_rate_limit("admin_operations")
async def deduct_user_points(
    request_data: PointDeductionRequest,
    request: Request
):
    """
    Deduct points from a user (Admin only)
    This endpoint allows admins to deduct points from users, typically used
    when scanning QR codes for penalty/reward systems.
    """
    try:
        # Get admin user ID for audit trail
        admin_id = get_current_user_id(request)

        # Validate user exists
        users = read_users()
        user_exists = any(u["id"] == request_data.user_id for u in users)

        if not user_exists:
            raise ValidationError(f"User with ID '{request_data.user_id}' not found")

        # Validate points amount
        if request_data.points <= 0:
            raise ValidationError("Points to deduct must be greater than 0")

        if request_data.points > 10000:
            raise ValidationError("Cannot deduct more than 10,000 points at once")

        # Get current user points
        current_points = get_user_points(request_data.user_id)
        user_current_points = current_points.get("total_points", 0)

        # Check if user has enough points
        if user_current_points < request_data.points:
            raise BusinessLogicError(
                f"Insufficient points. User has {user_current_points} points, trying to deduct {request_data.points}"
            )

        # Deduct points
        success, message = deduct_points_from_user(
            user_id=request_data.user_id,
            points=request_data.points,
            reason=request_data.reason,
            admin_id=admin_id
        )

        if not success:
            raise DatabaseError(f"Failed to deduct points: {message}")

        # Get updated points for response
        updated_points = get_user_points(request_data.user_id)

        # Log the action
        logger.info(
            f"Admin {admin_id} deducted {request_data.points} points from user {request_data.user_id}. "
            f"Reason: {request_data.reason}"
        )

        # Track in structured logging
        track_error(
            "points_deducted",
            f"Admin deducted {request_data.points} points from user {request_data.user_id}",
            request=request,
            extra_data={
                "admin_id": admin_id,
                "target_user_id": request_data.user_id,
                "points_deducted": request_data.points,
                "reason": request_data.reason,
                "remaining_points": updated_points.get("total_points", 0)
            }
        )

        return {
            "success": True,
            "message": f"Successfully deducted {request_data.points} points from user",
            "user_id": request_data.user_id,
            "points_deducted": request_data.points,
            "remaining_points": updated_points.get("total_points", 0),
            "reason": request_data.reason,
            "admin_id": admin_id,
            "timestamp": datetime.now(IST).isoformat()
        }

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except BusinessLogicError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        track_error("admin_deduct_points_failed", str(e), request=request)
        raise HTTPException(status_code=500, detail=f"Failed to deduct points: {str(e)}")

@router.post("/award-points", response_model=Dict[str, Any])
@require_role(UserRole.ADMIN)
@api_rate_limit("admin_operations")
async def award_user_points(
    request_data: PointAwardRequest,
    request: Request
):
    """
    Award points to a user (Admin only)
    This endpoint allows admins to manually award points to users.
    """
    try:
        # Get admin user ID for audit trail
        admin_id = get_current_user_id(request)

        # Validate user exists
        users = read_users()
        user_exists = any(u["id"] == request_data.user_id for u in users)

        if not user_exists:
            raise ValidationError(f"User with ID '{request_data.user_id}' not found")

        # Validate points amount
        if request_data.points <= 0:
            raise ValidationError("Points to award must be greater than 0")

        if request_data.points > 10000:
            raise ValidationError("Cannot award more than 10,000 points at once")

        # Award points
        success = award_points_to_user(
            user_id=request_data.user_id,
            points=request_data.points,
            reason=request_data.reason
        )

        if not success:
            raise DatabaseError("Failed to award points")

        # Get updated points for response
        updated_points = get_user_points(request_data.user_id)

        # Log the action
        logger.info(
            f"Admin {admin_id} awarded {request_data.points} points to user {request_data.user_id}. "
            f"Reason: {request_data.reason}"
        )

        # Track in structured logging
        track_error(
            "points_awarded",
            f"Admin awarded {request_data.points} points to user {request_data.user_id}",
            request=request,
            extra_data={
                "admin_id": admin_id,
                "target_user_id": request_data.user_id,
                "points_awarded": request_data.points,
                "reason": request_data.reason,
                "total_points": updated_points.get("total_points", 0)
            }
        )

        return {
            "success": True,
            "message": f"Successfully awarded {request_data.points} points to user",
            "user_id": request_data.user_id,
            "points_awarded": request_data.points,
            "total_points": updated_points.get("total_points", 0),
            "reason": request_data.reason,
            "admin_id": admin_id,
            "timestamp": datetime.now(IST).isoformat()
        }

    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        track_error("admin_award_points_failed", str(e), request=request)
        raise HTTPException(status_code=500, detail=f"Failed to award points: {str(e)}")

@router.get("/user-points/{user_id}", response_model=UserPointsResponse)
@require_role(UserRole.ADMIN)
@api_rate_limit("admin_operations")
async def get_user_points_admin(
    user_id: str,
    request: Request
):
    """
    Get detailed points information for a user (Admin only)
    Returns current points and transaction history for audit purposes.
    """
    try:
        # Validate user exists
        users = read_users()
        user_exists = any(u["id"] == user_id for u in users)

        if not user_exists:
            raise ValidationError(f"User with ID '{user_id}' not found")

        # Get user points details
        user_points = get_user_points(user_id)

        return UserPointsResponse(
            user_id=user_id,
            current_points=user_points.get("total_points", 0),
            transaction_history=user_points.get("transaction_history", [])
        )

    except ValidationError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        track_error("admin_get_user_points_failed", str(e), request=request)
        raise HTTPException(status_code=500, detail=f"Failed to get user points: {str(e)}")

@router.get("/users-with-points", response_model=List[Dict[str, Any]])
@require_role(UserRole.ADMIN)
@api_rate_limit("admin_operations")
async def get_users_with_points(
    request: Request,
    min_points: int = Query(0, ge=0, description="Minimum points threshold"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of users to return")
):
    """
    Get list of users with their points (Admin only)
    Useful for admin dashboard to see users with points above a threshold.
    """
    try:
        # Get all users with points
        all_points = read_user_points()

        # Filter by minimum points and limit results
        filtered_users = [
            {
                "user_id": points["id"],
                "total_points": points.get("total_points", 0),
                "transaction_count": len(points.get("transaction_history", []))
            }
            for points in all_points
            if points.get("total_points", 0) >= min_points
        ][:limit]

        # Sort by points descending
        filtered_users.sort(key=lambda x: x["total_points"], reverse=True)

        return {
            "users": filtered_users,
            "count": len(filtered_users),
            "min_points_threshold": min_points
        }

    except Exception as e:
        track_error("admin_get_users_with_points_failed", str(e), request=request)
        raise HTTPException(status_code=500, detail=f"Failed to get users with points: {str(e)}")

@router.get("/points-transactions", response_model=List[Dict[str, Any]])
@require_role(UserRole.ADMIN)
@api_rate_limit("admin_operations")
async def get_points_transactions(
    request: Request,
    limit: int = Query(100, ge=1, le=500, description="Maximum number of transactions to return"),
    user_id: str = Query(None, description="Filter by specific user ID")
):
    """
    Get recent points transactions (Admin only)
    Useful for audit trail and monitoring point system activity.
    """
    try:
        # Get all users with points
        all_points = read_user_points()

        all_transactions = []

        for points in all_points:
            user_transactions = points.get("transaction_history", [])

            for transaction in user_transactions:
                transaction_entry = {
                    "user_id": points["id"],
                    "timestamp": transaction.get("timestamp"),
                    "type": transaction.get("type"),
                    "points": transaction.get("points"),
                    "reason": transaction.get("reason"),
                    "admin_id": transaction.get("admin_id")
                }
                all_transactions.append(transaction_entry)

        # Filter by user_id if provided
        if user_id:
            all_transactions = [t for t in all_transactions if t["user_id"] == user_id]

        # Sort by timestamp descending (most recent first)
        all_transactions.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        # Limit results
        limited_transactions = all_transactions[:limit]

        return {
            "transactions": limited_transactions,
            "count": len(limited_transactions),
            "total_transactions": len(all_transactions)
        }

    except Exception as e:
        track_error("admin_get_points_transactions_failed", str(e), request=request)
        raise HTTPException(status_code=500, detail=f"Failed to get points transactions: {str(e)}")

@router.get("/qr-lookup/{user_id}", response_model=Dict[str, Any])
@require_role(UserRole.ADMIN)
@api_rate_limit("admin_operations")
async def lookup_user_by_qr(
    user_id: str,
    request: Request
):
    """
    Lookup user information by QR code user ID (Admin only)
    This endpoint helps admins verify user identity when scanning QR codes.
    """
    try:
        # Validate user exists
        users = read_users()
        user = next((u for u in users if u["id"] == user_id), None)

        if not user:
            raise ValidationError(f"User with ID '{user_id}' not found")

        # Get user points
        user_points = get_user_points(user_id)

        # Build response (exclude sensitive information)
        user_info = {
            "id": user["id"],
            "name": user["name"],
            "phone": user.get("phone"),
            "email": user.get("email"),
            "current_points": user_points.get("total_points", 0),
            "points_transactions_count": len(user_points.get("transaction_history", [])),
            "created_at": user.get("createdAt"),
            "is_private": user.get("is_private", False)
        }

        # Log the lookup for audit
        admin_id = get_current_user_id(request)
        logger.info(f"Admin {admin_id} looked up user {user_id} via QR code")

        track_error(
            "user_qr_lookup",
            f"Admin looked up user {user_id}",
            request=request,
            extra_data={
                "admin_id": admin_id,
                "target_user_id": user_id,
                "user_name": user.get("name")
            }
        )

        return {
            "success": True,
            "user": user_info,
            "message": f"User {user['name']} found with {user_points.get('total_points', 0)} points"
        }

    except ValidationError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        track_error("admin_qr_lookup_failed", str(e), request=request)
        raise HTTPException(status_code=500, detail=f"Failed to lookup user: {str(e)}")
