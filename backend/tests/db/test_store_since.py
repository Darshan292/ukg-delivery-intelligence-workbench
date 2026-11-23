# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""save(..., since=) writes only the rows a Records has beyond `since`. FICTIONAL data."""

import pytest
from sqlalchemy import Engine, text

from app.domain.model import Actor, Document, DocumentVersion, Entity
from app.domain.records import Records
from app.store import load, save
from tests.db_helpers import norm
from tests.domain.builders import World

SHA = "a" * 64


def base() -> Records:
    w = World()
    w.reviewer()
    w.snapshot("s1")
    return w.build()


def grown(b: Records) -> Records:
    return b.extended(
        documents=(Document(id=1, product_profile="synthetic", title="d"),),
        document_versions=(
            DocumentVersion(
                id=1, document_id=1, sha256=SHA, snapshot_id=1, supersedes_version_id=None,
                declared_by=b.actors[0].id, uploaded_at=b.snapshots[0].captured_at,
            ),
        ),
        entities=(Entity(id=1, product_profile="synthetic", entity_type="req", natural_key="Q"),),
    )  # fmt: skip


def count(store: Engine, table: str) -> int:
    with store.connect() as c:
        return int(c.scalar(text(f"SELECT count(*) FROM {table}")) or 0)  # noqa: S608


def test_since_writes_suffix_only(store: Engine, ingest_engine: Engine) -> None:
    b = base()
    with store.begin() as c:
        save(c, b)  # as the owner: catalogue, actors, snapshot
    r = grown(b)
    with ingest_engine.begin() as c:  # a role that may not write actors or the catalogue
        save(c, r, since=b)
    with store.connect() as c:
        assert norm(load(c)) == norm(r)


def test_since_not_a_prefix(store: Engine, ingest_engine: Engine) -> None:
    b = base()
    r = grown(b)
    longer = b.extended(actors=(Actor(id=9, kind="service", display_name="x", roles=frozenset()),))
    other = r.extended()  # same length as r in every field, different content in one
    swapped = Records.model_validate(
        {
            **{f: getattr(r, f) for f in Records.model_fields},
            "entities": (
                Entity(id=1, product_profile="synthetic", entity_type="req", natural_key="Z"),
            ),
        }
    )
    for since in (longer, swapped):
        with (
            pytest.raises(ValueError, match="save: since is not a prefix"),
            ingest_engine.begin() as c,
        ):
            save(c, other, since=since)
    assert count(store, "entity") == 0 and count(store, "document") == 0  # nothing written


def test_since_none_unchanged(store: Engine) -> None:
    r = grown(base())
    with store.begin() as c:
        save(c, r)
    with store.connect() as c:
        assert norm(load(c)) == norm(r)
