# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors

from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import Engine, inspect
from sqlalchemy.engine import URL
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from app.models import Base, Entity, Relationship

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def migrated(db_engine: Engine, db_url: URL) -> Engine:
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    cfg.attributes["url"] = db_url.render_as_string(hide_password=False)
    command.upgrade(cfg, "head")
    command.upgrade(cfg, "head")  # idempotent: second run is a no-op
    return db_engine


def test_migration_upgrade_twice_ok(migrated: Engine) -> None:
    tables = set(inspect(migrated).get_table_names())
    assert {"entity", "relationship", "evidence_locator"} <= tables


def _entity(s: Session, key: str, profile: str = "synthetic") -> Entity:
    e = Entity(
        product_profile=profile, entity_type="requirement", natural_key=key, label="Fictional"
    )
    s.add(e)
    s.flush()
    return e


def test_entity_profile_check_rejects_bad_profile(migrated: Engine) -> None:
    with Session(migrated) as s, pytest.raises(DBAPIError, match="ck_entity_product_profile"):
        _entity(s, "REQ-X", profile="made_up")


def test_entity_unique_natural_key(migrated: Engine) -> None:
    with Session(migrated) as s:
        _entity(s, "REQ-U")
        s.commit()
    with Session(migrated) as s, pytest.raises(IntegrityError):
        _entity(s, "REQ-U")


def test_relationship_rejects_self_link(migrated: Engine) -> None:
    with Session(migrated) as s:
        e = _entity(s, "REQ-S")
        s.add(Relationship(type="implements", source_entity_id=e.id, target_entity_id=e.id))
        with pytest.raises(DBAPIError, match="ck_relationship_no_self"):
            s.flush()


def test_models_match_migration(migrated: Engine) -> None:
    with migrated.connect() as conn:
        ctx = MigrationContext.configure(conn)
        assert compare_metadata(ctx, Base.metadata) == []


@pytest.mark.parametrize("profile", ["synthetic", "ukg_pro_wfm", "workforce_central", "unknown"])
def test_entity_accepts_approved_profiles(migrated: Engine, profile: str) -> None:
    with Session(migrated) as s:
        _entity(s, f"K-{profile}", profile=profile)
        s.rollback()


def test_duplicate_relationship_rejected(migrated: Engine) -> None:
    with Session(migrated) as s:
        a, b = _entity(s, "D-A"), _entity(s, "D-B")
        s.add(Relationship(type="implements", source_entity_id=a.id, target_entity_id=b.id))
        s.flush()
        s.add(Relationship(type="implements", source_entity_id=a.id, target_entity_id=b.id))
        with pytest.raises(IntegrityError):
            s.flush()
        s.rollback()
