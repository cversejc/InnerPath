from app.main import app


def test_report_router_keeps_task_and_report_endpoints_registered():
    routes = {
        (route.path, method)
        for route in app.routes
        for method in (route.methods or set())
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
