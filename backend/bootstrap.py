"""
Deja importable el código de rag_engine/ (core.py, logger.py,
rag_langgraph/, report_generator/) sin duplicarlo ni reescribirlo.

Se importa (por su solo efecto de módulo) antes de cualquier `from core
import ...` / `from logger import ...` / `from rag_langgraph...`, en
main.py y en cada service que lo necesite — así funciona sin importar el
orden real de imports de uvicorn.
"""
import os
import sys

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
ENGINE_DIR = os.path.join(PROJECT_ROOT, "rag_engine")
APP_DIR = os.path.join(ENGINE_DIR, "app")

for _path in (ENGINE_DIR, APP_DIR):
    if _path not in sys.path:
        sys.path.insert(0, _path)
