# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""Every table is append-only at the trigger layer, independent of privileges (owner connects)."""

import pytest
from sqlalchemy import Engine, text

from tests.db_helpers import TABLES, Ids, sqlstate_raised


def _column(c: object, table: str) -> str:
    # first ordinary column: GENERATED ALWAYS and identity columns reject SET col = col first
    return c.scalar(  # type: ignore[attr-defined]
        text(
            "SELECT column_name FROM information_schema.columns WHERE table_schema = 'public'"
            " AND table_name = :t AND is_generated = 'NEVER' AND is_identity = 'NO'"
            " ORDER BY ordinal_position LIMIT 1"
        ),
        {"t": table},
    )


def test_every_table_has_append_only_trigger(store: Engine) -> None:
    with store.connect() as c:
        rows = c.execute(
            text(
                "SELECT c.relname FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid"
                " WHERE t.tgname = 'wb_append_only' AND NOT t.tgisinternal"
            )
        ).all()
    assert sorted(r[0] for r in rows) == sorted(TABLES)


@pytest.mark.parametrize("table", TABLES)
def test_owner_update_blocked(store: Engine, table: str) -> None:
    # WHERE false: a row-level trigger would never fire, the statement-level one does
    with store.connect() as c:
        col = _column(c, table)
    with sqlstate_raised("WB001"), store.begin() as c:
        c.execute(text(f"UPDATE {table} SET {col} = {col} WHERE false"))  # noqa: S608


@pytest.mark.parametrize("table", TABLES)
def test_owner_delete_blocked(store: Engine, table: str) -> None:
    with sqlstate_raised("WB001"), store.begin() as c:
        c.execute(text(f"DELETE FROM {table} WHERE false"))  # noqa: S608


def test_actor_kind_cannot_change(store: Engine, world_ids: Ids) -> None:
    with sqlstate_raised("WB001"), store.begin() as c:
        c.execute(
            text("UPDATE actor SET kind = 'human', roles = '{reviewer}' WHERE id = :a"),
            {"a": world_ids.service},
        )
    with store.connect() as c:
        row = c.execute(
            text("SELECT kind, roles FROM actor WHERE id = :a"), {"a": world_ids.service}
        ).one()
    assert row.kind == "service" and row.roles == []
