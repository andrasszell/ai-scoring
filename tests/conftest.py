import pytest

from evidence_collection.db import apply_migrations, connect


@pytest.fixture()
def conn(tmp_path):
    c = connect(tmp_path / "test.sqlite")
    apply_migrations(c)
    yield c
    c.close()
