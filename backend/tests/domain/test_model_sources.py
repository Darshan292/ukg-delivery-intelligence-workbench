# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import ValidationError

from app.domain.model import Actor, Document, DocumentVersion, Snapshot

T = datetime(2026, 1, 1, tzinfo=UTC)
SHA = "a" * 64


def actor(**kw: Any) -> Actor:
    d: dict[str, Any] = {
        "id": 1,
        "kind": "service",
        "display_name": "Svc",
        "roles": frozenset[str](),
    }
    return Actor(**{**d, **kw})


def dv(**kw: Any) -> DocumentVersion:
    d: dict[str, Any] = {
        "id": 1,
        "document_id": 1,
        "sha256": SHA,
        "snapshot_id": None,
        "supersedes_version_id": None,
        "declared_by": 1,
        "uploaded_at": T,
    }
    return DocumentVersion(**{**d, **kw})


def test_actor_kind_is_immutable() -> None:
    with pytest.raises(ValidationError):
        actor().kind = "human"  # pyright: ignore[reportAttributeAccessIssue]


@pytest.mark.parametrize("name", ["", "   "])
def test_actor_display_name_required(name: str) -> None:
    with pytest.raises(ValidationError):
        actor(display_name=name)


def test_actor_is_reviewer() -> None:
    rev = frozenset({"reviewer"})
    assert actor(kind="human", roles=rev).is_reviewer
    assert not actor(kind="human", roles=frozenset({"x"})).is_reviewer
    assert not actor(kind="service", roles=rev).is_reviewer


def test_snapshot_requires_aware_capture_time() -> None:
    ok: dict[str, Any] = {
        "id": 1,
        "product_profile": "synthetic",
        "environment": "dev",
        "label": "s1",
        "captured_at": T,
    }
    assert Snapshot(**ok)
    bads: list[dict[str, Any]] = [
        {"captured_at": datetime(2026, 1, 1)},  # noqa: DTZ001
        {"environment": ""},
        {"label": " "},
    ]
    for bad in bads:
        merged: dict[str, Any] = {**ok, **bad}
        with pytest.raises(ValidationError):
            Snapshot(**merged)


def test_document_title_required() -> None:
    assert Document(id=1, product_profile="synthetic", title="t")
    with pytest.raises(ValidationError):
        Document(id=1, product_profile="synthetic", title="")


@pytest.mark.parametrize("sha", [SHA, "0123456789abcdef" * 4])
def test_document_version_sha256_accepts(sha: str) -> None:
    assert dv(sha256=sha)


@pytest.mark.parametrize("sha", ["A" * 64, "a" * 63, "g" * 64, "a" * 65])
def test_document_version_sha256_rejects(sha: str) -> None:
    with pytest.raises(ValidationError):
        dv(sha256=sha)


def test_document_version_cannot_supersede_itself() -> None:
    with pytest.raises(ValidationError):
        dv(id=4, supersedes_version_id=4)


def test_document_version_snapshot_optional() -> None:
    assert dv(snapshot_id=None).snapshot_id is None
