"""Read-only provider diagnostic; never prints credentials."""
import asyncio
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.db.session import AsyncSessionLocal, engine
from app.domains.llm.service import list_configurations, runtime_config_from_row, runtime_config_from_environment
from app.services.llm import chat
import httpx

async def main():
    async with AsyncSessionLocal() as db:
        rows = await list_configurations(db)
        configs = [(str(r.id), runtime_config_from_row(r)) for r in rows]
        try:
            configs.append(("environment", runtime_config_from_environment()))
        except ValueError:
            pass
        for identity, config in configs:
            data = {"configuration": identity, "provider": config.provider, "base_url": config.base_url, "model": config.model}
            try:
                result = await chat([{"role":"user", "content":"Reply OK only."}], configuration=config, max_tokens=64, timeout_seconds=30, thinking=False)
                data.update(status="OK", response=result.content)
            except httpx.HTTPStatusError as error:
                data.update(status=error.response.status_code, response=error.response.text[:500].replace(config.api_key,"[redacted]"))
            except Exception as error:
                data.update(error=str(error) if isinstance(error, ValueError) else type(error).__name__)
            print(json.dumps(data,ensure_ascii=False),flush=True)
    await engine.dispose()
asyncio.run(main())
