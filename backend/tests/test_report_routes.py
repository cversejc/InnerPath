from app.main import app


def test_report_router_keeps_task_and_report_endpoints_registered():
    routes = {
        (path, method.upper())
        for path, operations in app.openapi()["paths"].items()
        for method in operations
        if method.lower() in {"get", "post", "put", "patch", "delete", "options", "head"}
    }

    assert {
        ("/api/v1/reports", "POST"),
        ("/api/v1/reports/tasks/{task_id}", "GET"),
        ("/api/v1/reports/staff/tasks/{task_id}", "GET"),
        ("/api/v1/reports", "GET"),
        ("/api/v1/reports/staff/users/{user_id}", "GET"),
        ("/api/v1/reports/admin/users/{user_id}", "GET"),
        ("/api/v1/reports/latest/context", "GET"),
        ("/api/v1/reports/{report_id}", "GET"),
        ("/api/v1/reports/{report_id}", "DELETE"),
    }.issubset(routes)
