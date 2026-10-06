import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.audit_context import audit_context_from_request
from fastapi import Request

from app.db.session import get_db
from app.dependencies import require_roles
from app.domains.audit.service import record_audit
from app.domains.llm.models import LLMProviderConfig
from app.domains.llm.schemas import (
    LLMConfigurationListResponse,
    LLMConfigurationResponse,
    LLMConfigurationTest,
    LLMConfigurationWrite,
    LLMTestResponse,
)
from app.domains.llm.service import (
    configuration_response,
    delete_configuration,
    environment_fallback_summary,
    list_configurations,
    resolve_runtime_config,
    save_configuration,
    set_default_configuration,
)
from app.models.user import User
from app.services.llm import chat

router = APIRouter()


def _audit_payload(row: LLMProviderConfig) -> dict:
    return {
        "name": row.name,
        "provider": row.provider,
        "base_url": row.base_url,
        "model": row.model,
        "is_default": row.is_default,
    }


async def _record_config_change(
    db: AsyncSession,
    actor: User,
    action: str,
    row: LLMProviderConfig,
    request: Request,
) -> None:
    await record_audit(
        db,
        actor.id,
        action,
        "llm_provider_config",
        str(row.id),
        details=_audit_payload(row),
        audit_context=audit_context_from_request(request),
    )


@router.get(
    "/llm/configurations", response_model=LLMConfigurationListResponse
)
async def list_llm_configurations(
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    rows = await list_configurations(db)
    return {
        "items": [configuration_response(row) for row in rows],
        "environment_fallback": environment_fallback_summary(),
    }


@router.post(
    "/llm/configurations",
    response_model=LLMConfigurationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_llm_configuration(
    payload: LLMConfigurationWrite,
    request: Request,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    try:
        row = await save_configuration(db, payload, actor_id=current_user.id)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    await _record_config_change(db, current_user, "admin.llm_config.created", row, request)
    await db.commit()
    await db.refresh(row)
    return configuration_response(row)


@router.put(
    "/llm/configurations/{configuration_id}",
    response_model=LLMConfigurationResponse,
)
async def update_llm_configuration(
    configuration_id: int,
    payload: LLMConfigurationWrite,
    request: Request,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    try:
        row = await save_configuration(
            db,
            payload,
            actor_id=current_user.id,
            configuration_id=configuration_id,
        )
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    await _record_config_change(db, current_user, "admin.llm_config.updated", row, request)
    await db.commit()
    await db.refresh(row)
    return configuration_response(row)


@router.post(
    "/llm/configurations/{configuration_id}/default",
    response_model=LLMConfigurationResponse,
)
async def make_llm_configuration_default(
    configuration_id: int,
    request: Request,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    try:
        row = await set_default_configuration(db, configuration_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    await _record_config_change(db, current_user, "admin.llm_config.default_changed", row, request)
    await db.commit()
    await db.refresh(row)
    return configuration_response(row)


@router.delete("/llm/configurations/{configuration_id}", status_code=204)
async def remove_llm_configuration(
    configuration_id: int,
    request: Request,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    try:
        name = await delete_configuration(db, configuration_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    await record_audit(
        db,
        current_user.id,
        "admin.llm_config.deleted",
        "llm_provider_config",
        str(configuration_id),
        details={"name": name},
        audit_context=audit_context_from_request(request),
    )
    await db.commit()


@router.post("/llm/configurations/test", response_model=LLMTestResponse)
async def test_llm_configuration(
    payload: LLMConfigurationTest,
    current_user: User = Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    write_payload = LLMConfigurationWrite.model_validate(
        payload.model_dump(exclude={"configuration_id"})
    )
    try:
        runtime_config = await resolve_runtime_config(
            db,
            configuration_id=payload.configuration_id,
            payload=write_payload,
        )
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    try:
        result = await chat(
            [
                {"role": "system", "content": "Reply with exactly OK."},
                {"role": "user", "content": "Connection test. Reply with exactly OK."},
            ],
            configuration=runtime_config,
            temperature=0,
            max_tokens=16,
            timeout_seconds=min(runtime_config.timeout_seconds, 20),
            thinking=False,
        )
    except httpx.TimeoutException as error:
        raise HTTPException(status_code=504, detail="模型服务连接超时") from error
    except httpx.HTTPStatusError as error:
        raise HTTPException(
            status_code=502,
            detail=f"模型服务返回 HTTP {error.response.status_code}",
        ) from error
    except (httpx.RequestError, ValueError) as error:
        raise HTTPException(
            status_code=502,
            detail="模型连接测试失败，请检查 API 地址、密钥和模型名称",
        ) from error

    return {
        "success": True,
        "provider": result.provider,
        "model": result.model,
        "latency_ms": result.latency_ms,
        "input_tokens": result.usage.get("input_tokens"),
        "output_tokens": result.usage.get("output_tokens"),
    }
