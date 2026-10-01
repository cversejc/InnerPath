import csv
import io
from datetime import date
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.admin_support import (
    BOOKING_STATUS_LABELS,
    REPORT_STATUS_LABELS,
    USER_ROLE_LABELS,
    _date_filter,
    _load_admin_bookings,
    _load_admin_reports,
    _load_audits,
    _load_decision_logs,
)
from app.config import settings
from app.db.session import get_db
from app.dependencies import require_roles
from app.models.user import User

router = APIRouter()


def _csv_response(filename: str, headers: list[str], rows: list[list[Any]]) -> Response:
    buffer = io.StringIO()
    buffer.write("\ufeff")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(headers)
    writer.writerows(rows)
    return Response(content=buffer.getvalue(), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{filename}"'})

@router.get("/exports/{resource}.csv")
async def export_admin_resource(
    resource: str,
    request: Request,
    search: Optional[str] = Query(None, max_length=100),
    role: Optional[str] = Query(None, pattern="^(user|consultant|admin)$"),
    is_active: Optional[bool] = None,
    record_status: Optional[str] = Query(None, alias="status"),
    consultant_id: Optional[int] = None,
    user_id: Optional[int] = None,
    action: Optional[str] = Query(None, max_length=100),
    resource_type: Optional[str] = Query(None, max_length=50),
    actor_user_id: Optional[int] = None,
    target_user_id: Optional[int] = None,
    ai_model: Optional[str] = Query(None, max_length=50),
    created_from: Optional[date] = None,
    created_to: Optional[date] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    limit = settings.ADMIN_EXPORT_MAX_ROWS
    if resource == "users":
        conditions = []
        if search:
            conditions.append(or_(User.name.ilike(f"%{search}%"), User.phone.ilike(f"%{search}%")))
        if role:
            conditions.append(User.role == role)
        if is_active is not None:
            conditions.append(User.is_active == is_active)
        conditions.extend(_date_filter(User.created_at, created_from or date_from, created_to or date_to))
        statement = select(User).order_by(User.created_at.desc()).limit(limit)
        if conditions:
            statement = statement.where(*conditions)
        users = (await db.execute(statement)).scalars().all()
        rows = [[user.id, user.name, user.phone, USER_ROLE_LABELS.get(user.role, user.role), "正常" if user.is_active else "已停用", user.created_at, user.last_login_at] for user in users]
        return _csv_response("users.csv", ["ID", "姓名", "手机号", "角色", "状态", "注册时间", "最近登录"], rows)
    if resource == "bookings":
        items, _ = await _load_admin_bookings(db, booking_status=record_status, consultant_id=consultant_id, user_id=user_id, search=search, date_from=date_from, date_to=date_to, page=1, size=limit)
        rows = [[item["id"], item["user_name"], item["user_phone"], item["service_name"], BOOKING_STATUS_LABELS.get(item["status"], item["status"]), item["consultant_name"], item["confirmed_date"], item["confirmed_time"], item["created_at"]] for item in items]
        return _csv_response("bookings.csv", ["ID", "用户", "联系方式", "服务", "状态", "咨询师", "确认日期", "确认时间", "创建时间"], rows)
    if resource == "reports":
        items, _ = await _load_admin_reports(db, report_status=record_status, user_id=user_id, search=search, ai_model=ai_model, date_from=date_from, date_to=date_to, page=1, size=limit)
        rows = [[item["id"], item["user_name"], item["user_phone"], item["title"], REPORT_STATUS_LABELS.get(item["status"], item["status"]), item["ai_model"], item["generation_time_ms"], item["created_at"]] for item in items]
        return _csv_response("reports.csv", ["ID", "用户", "联系方式", "标题", "状态", "模型", "生成耗时(ms)", "创建时间"], rows)
    if resource == "decision-logs":
        items, _ = await _load_decision_logs(db, user_id=user_id, log_status=record_status, search=search, date_from=date_from, date_to=date_to, page=1, size=limit)
        rows = [[item["id"], item["user_id"], item["user_name"], item["log_date"], item["kind"], item["status"], item["content"], item["note"], item["created_at"]] for item in items]
        return _csv_response("decision-logs.csv", ["ID", "用户ID", "用户", "记录日期", "类型", "状态", "内容", "备注", "创建时间"], rows)
    if resource == "audit-logs":
        items, _ = await _load_audits(db, action=action, resource_type=resource_type, actor_user_id=actor_user_id, target_user_id=target_user_id, search=search, date_from=date_from, date_to=date_to, page=1, size=limit)
        rows = [[item["id"], item["created_at"], item["action"], item["resource_type"], item["resource_id"], item["actor_name"] or item["actor_user_id"], item["target_user_name"] or item["target_user_id"], item["ip_address"], item["request_id"], item["details"]] for item in items]
        return _csv_response("audit-logs.csv", ["ID", "时间", "操作", "资源类型", "资源ID", "操作者", "目标用户", "IP", "请求ID", "详情"], rows)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unsupported export resource")
