import ast
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = BACKEND_ROOT / "app"
BOUNDARIES = {
    "domains": {"app.api", "app.application", "app.tasks"},
    "application": {"app.api", "app.tasks"},
}


def module_name_for(path: Path) -> str:
    parts = path.relative_to(APP_ROOT.parent).with_suffix("").parts
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def resolve_import_from(node: ast.ImportFrom, current_module: str, path: Path) -> str:
    if node.level == 0:
        return node.module or ""

    current_parts = current_module.split(".")
    package_parts = current_parts if path.name == "__init__.py" else current_parts[:-1]
    base_parts = package_parts[: len(package_parts) - node.level + 1]
    if node.module:
        base_parts.extend(node.module.split("."))
    return ".".join(base_parts)


def imported_modules(path: Path) -> set[str]:
    current_module = module_name_for(path)
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base_module = resolve_import_from(node, current_module, path)
            modules.add(base_module)
            modules.update(
                f"{base_module}.{alias.name}" if base_module else alias.name
                for alias in node.names
                if alias.name != "*"
            )

    return modules


def test_relative_import_resolution_reaches_root_adapters():
    path = APP_ROOT / "domains" / "users" / "service.py"
    node = ast.ImportFrom(module="api.audit_context", names=[], level=3)

    assert (
        resolve_import_from(node, "app.domains.users.service", path)
        == "app.api.audit_context"
    )


def test_domain_and_application_modules_do_not_import_adapters():
    violations = []

    for layer, forbidden_roots in BOUNDARIES.items():
        layer_root = APP_ROOT / layer
        for path in sorted(layer_root.rglob("*.py")):
            for imported_module in imported_modules(path):
                for forbidden_root in forbidden_roots:
                    if imported_module == forbidden_root or imported_module.startswith(
                        f"{forbidden_root}."
                    ):
                        relative_path = path.relative_to(BACKEND_ROOT)
                        violations.append(
                            f"{relative_path} imports {imported_module}; "
                            f"{layer} modules must not depend on {forbidden_root}"
                        )

    assert not violations, "\n".join(violations)
