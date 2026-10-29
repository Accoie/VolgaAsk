"""Глобальная настройка pytest для тестов поиска.

pytest загружает conftest.py до импорта тестовых модулей, поэтому здесь
добавляем корень проекта в sys.path — импорты в test_search.py остаются
обычными (без sys.path-хаков и noqa).
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
