import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import RAIZ  # noqa: E402
from core.fotos import CarpetaLocalFuenteFotos  # noqa: E402
from core.repositorio import MockRepositorio  # noqa: E402


@pytest.fixture
def repo():
    return MockRepositorio()


@pytest.fixture
def fuente():
    return CarpetaLocalFuenteFotos(RAIZ / "fixtures" / "fotos")
