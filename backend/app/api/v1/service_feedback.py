from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.audit_context import audit_context_from_request
from app.application.service_feedback import (
    list_my_service_feedback,
    submit_service_feedback,
)
from app.db.session import get_db
from app.dependencies import get_current_active_user
from app.domains.feedback.schemas import (
    MyServiceFeedbackItem,
    MyServiceFeedbackListResponse,
    ServiceFeedbackCreate,
)
from app.models.user import User

router = APIRouter()


@router.post("", response_model=MyServiceFeedbackItem, status_code=status.HTTP_201_CREATED)
async def create_my_service_feedback(
    data: ServiceFeedbackCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        feedback = await submit_service_feedback(
            db,
            user=current_user,
            data=data,
            audit_context=audit_context_from_request(request),
        )
        await db.commit()
        await db.refresh(feedback)
        return feedback
    except ValueError as error:
        await db.rollback()
        code = str(error)
        http_status = (
            status.HTTP_404_NOT_FOUND
            if code == "feedback_target_not_found"
            else status.HTTP_409_CONFLICT
            if code in {"feedback_target_not_delivered", "feedback_already_submitted"}
            else status.HTTP_422_UNPROCESSABLE_ENTITY
        )
        raise HTTPException(status_code=http_status, detail=code)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="feedback_already_submitted",
        )


@router.get("/mine", response_model=MyServiceFeedbackListResponse)
async def get_my_service_feedback(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return MyServiceFeedbackListResponse(
        items=await list_my_service_feedback(db, current_user.id)
    )
