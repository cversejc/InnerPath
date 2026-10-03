import asyncio
import json
import secrets
from urllib.parse import urlsplit

from app.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)
_render_slots = asyncio.Semaphore(2)


class ReportPdfRenderError(RuntimeError):
    pass


def _origin(url: str) -> str:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("REPORT_EXPORT_FRONTEND_URL must be an HTTP URL")
    return f"{parsed.scheme}://{parsed.netloc}"


async def render_report_pdf(
    report_id: int | str,
    report_payload: dict,
    user_payload: dict,
    *,
    preview: bool = False,
) -> bytes:
    try:
        from playwright.async_api import async_playwright

        frontend_url = settings.REPORT_EXPORT_FRONTEND_URL.rstrip("/")
        frontend_origin = _origin(frontend_url)
        report_path = f"/api/v1/reports/{report_id}"
        report_json = json.dumps(report_payload, ensure_ascii=False, separators=(",", ":"))
        user_json = json.dumps(user_payload, ensure_ascii=False, separators=(",", ":"))

        async with _render_slots:
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(
                    args=["--no-sandbox", "--disable-dev-shm-usage"]
                )
                try:
                    context = await browser.new_context(
                        viewport={"width": 1440, "height": 1000},
                        device_scale_factor=1,
                    )
                    page = await context.new_page()
                    page.set_default_timeout(20_000)

                    async def fulfill_json(route, payload):
                        await route.fulfill(
                            status=200,
                            content_type="application/json; charset=utf-8",
                            body=json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                        )

                    async def handle_request(route, request):
                        parsed = urlsplit(request.url)
                        if parsed.scheme in {"data", "blob"}:
                            await route.continue_()
                            return
                        if f"{parsed.scheme}://{parsed.netloc}" != frontend_origin:
                            await route.abort("blockedbyclient")
                            return
                        if parsed.path == "/api/v1/users/me" and request.method == "GET":
                            await fulfill_json(route, json.loads(user_json))
                            return
                        if parsed.path == report_path and request.method == "GET":
                            await fulfill_json(route, json.loads(report_json))
                            return
                        # Keep the renderer limited to the page assets and these two mocked reads.
                        if parsed.path.startswith("/api/"):
                            await route.abort("blockedbyclient")
                            return
                        await route.continue_()

                    await page.route("**/*", handle_request)
                    await context.add_init_script(
                        "window.sessionStorage.setItem('access_token', "
                        f"{json.dumps(secrets.token_urlsafe(24))});"
                    )
                    await page.goto(
                        f"{frontend_url}/#/pages/report/detail?id={report_id}"
                        f"{'&preview=1' if preview else ''}",
                        wait_until="domcontentloaded",
                        timeout=30_000,
                    )
                    await page.wait_for_selector('.report-document[data-render-ready="true"]')
                    await page.emulate_media(media="print")
                    await page.evaluate(
                        """async () => {
                          await document.fonts.ready;
                          await Promise.all(Array.from(document.images, image => image.decode().catch(() => {})));
                        }"""
                    )
                    return await page.pdf(
                        format="A4",
                        print_background=True,
                        prefer_css_page_size=True,
                        display_header_footer=False,
                    )
                finally:
                    await browser.close()
    except ReportPdfRenderError:
        raise
    except Exception as error:
        logger.exception("Report PDF rendering failed", extra={"report_id": report_id})
        raise ReportPdfRenderError("Could not render report PDF") from error
