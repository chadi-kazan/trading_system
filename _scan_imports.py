import ast
import importlib
from pathlib import Path

root = Path('.')
modules = set()
for path in root.rglob('*.py'):
    if path.is_file():
        try:
            tree = ast.parse(path.read_text(encoding='utf-8'))
        except Exception:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name:
                        modules.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.level == 0:
                    modules.add(node.module.split('.')[0])

missing = []
for module in sorted(modules):
    try:
        importlib.import_module(module)
    except ModuleNotFoundError:
        missing.append(module)

print('MISSING_MODULES=', missing)
