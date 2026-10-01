from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_active_user
from app.models.user import User
from app.schemas.service_request import (
    ServiceRequestCreate,
    ServiceRequestListResponse,
    ServiceRequestResponse,
    ServiceRequestUpdate,
)
from app.services.service_request_service import (
    create_service_request,
    get_service_request,
    get_user_service_requests,
    resubmit_service_request,
    update_user_service_request,
    withdraw_service_request,
)
from app.api.v1.service_request_api_support import _raise_value_error, _serialize_public

router = APIRouter()
@router.post("", response_model=ServiceRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_request(
    data: ServiceRequestCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        service_request = await create_service_request(db, current_user, data, request=request)
    except ValueError as error:
        _raise_value_error(error)
    return await _serialize_public(db, service_request)


@router.get("", response_model=ServiceRequestListResponse)
async def list_my_requests(
    request_status: Optional[str] = Query(None, alias="status", max_length=30),
    service_type: Optional[str] = Query(None, pattern="^(report|calendar)$"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    items = await get_user_service_requests(db, current_user.id, request_status, service_type)
    return ServiceRequestListResponse(items=[await _serialize_public(db, item) for item in items], total=len(items))


@router.get("/{request_id}", response_model=ServiceRequestResponse)
async def get_my_request(
    request_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service_request = await get_service_request(db, request_id)
    if not service_request or service_request.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service request not found")
    return await _serialize_public(db, service_request)


@router.patch("/{request_id}", response_model=ServiceRequestResponse)
async def update_my_request(
    request_id: int,
    data: ServiceRequestUpdate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service_request = await get_service_request(db, request_id)
    if not service_request or service_request.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service request not found")
    try:
        service_request = await update_user_service_request(db, service_request, current_user, data, request=request)
    except ValueError as error:
        _raise_value_error(error)
    return await _serialize_public(db, service_request)


@router.post("/{request_id}/resubmit", response_model=ServiceRequestResponse)
async def resubmit_my_request(
    request_id: int,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service_request = await get_service_request(db, request_id)
    if not service_request or service_request.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service request not found")
    try:
        service_request = await resubmit_service_request(db, service_request, current_user, request=request)
    except ValueError as error:
        _raise_value_error(error)
    return await _serialize_public(db, service_request)


@router.post("/{request_id}/withdraw", response_model=ServiceRequestResponse)
async def withdraw_my_request(
    request_id: int,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    service_request = await get_service_request(db, request_id)
    if not service_request or service_request.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service request not found")
    try:
        service_request = await withdraw_service_request(db, service_request, current_user, request=request)
    except ValueError as error:
        _raise_value_error(error)
    return await _serialize_public(db, service_request)


