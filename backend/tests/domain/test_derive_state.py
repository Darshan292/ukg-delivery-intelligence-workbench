# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""FICTIONAL: not UKG behaviour."""

from decimal import Decimal

import pytest
from hypothesis import given, settings

from app.domain.derive import edge_state, live_claims, verdict
from app.domain.records import Records
from tests.domain.builders import World
from tests.domain.strategies import worlds


class Fx:
    def __init__(self, w: World) -> None:
        self.w = w
        self.s1, self.s2 = w.snapshot("s1"), w.snapshot("s2")
        self.e1, self.e2, self.d = w.export(self.s1), w.export(self.s2), w.design()
        self.a, self.b, self.c = w.entity("cfg", "A"), w.entity("cfg", "B"), w.entity("cfg", "C")
        self.q = w.entity("req", "Q")
        self.uses = w.rel("uses", self.a, self.b)
        self.impl = w.rel("implements", self.a, self.q)


@pytest.fixture
def fx(world: World) -> Fx:
    return Fx(world)


def test_confidence_one_rule_claim_is_unreviewed(fx: Fx) -> None:
    fx.w.claim(fx.uses, fx.d, basis="deterministic_rule", confidence=Decimal(1))
    st = edge_state(fx.w.build(), fx.uses.id, fx.s1.id)
    assert (st.state, st.label) == ("unreviewed", "INFERRED")


def test_explicit_unreviewed_label_observed(fx: Fx) -> None:
    fx.w.claim(fx.uses, fx.d)
    st = edge_state(fx.w.build(), fx.uses.id, fx.s1.id)
    assert (st.state, st.label, st.basis_strength) == ("unreviewed", "OBSERVED", "explicit_source")


def test_accepted_label_confirmed(fx: Fx) -> None:
    fx.w.claim(fx.uses, fx.d)
    fx.w.accept(fx.uses, fx.s1)
    assert edge_state(fx.w.build(), fx.uses.id, fx.s1.id).label == "CONFIRMED"


def test_hidden_states_have_no_label(fx: Fx) -> None:
    fx.w.claim(fx.uses, fx.d)
    fx.w.reject(fx.uses, fx.s1)
    fx.w.supersede(fx.impl, None, fx.w.rel("implements", fx.a, fx.w.entity("req", "R")))
    r = fx.w.build()
    rejected = edge_state(r, fx.uses.id, fx.s1.id)
    superseded = edge_state(r, fx.impl.id, fx.s1.id)
    unsupported = edge_state(r, r.relationships[2].id, fx.s1.id)
    assert [x.state for x in (rejected, superseded, unsupported)] == [
        "rejected",
        "superseded",
        "unsupported",
    ]
    assert all(x.label is None for x in (rejected, superseded, unsupported))


def test_rejecting_stronger_claim_drops_basis_keeps_unreviewed(fx: Fx) -> None:
    ex = fx.w.claim(fx.uses, fx.d)
    fx.w.claim(fx.uses, fx.d, basis="deterministic_rule")
    assert edge_state(fx.w.build(), fx.uses.id, fx.s1.id).basis_strength == "explicit_source"
    fx.w.reject_claim(ex)
    st = edge_state(fx.w.build(), fx.uses.id, fx.s1.id)
    assert (st.state, st.basis_strength) == ("unreviewed", "deterministic_rule")


def test_rejecting_last_claim_gives_unsupported_not_rejected(fx: Fx) -> None:
    c = fx.w.claim(fx.uses, fx.d)
    fx.w.reject_claim(c)
    assert edge_state(fx.w.build(), fx.uses.id, fx.s1.id).state == "unsupported"


def test_only_absent_claims_and_no_verdict_is_unsupported(fx: Fx) -> None:
    fx.w.claim(fx.uses, fx.d, polarity="absent")
    assert edge_state(fx.w.build(), fx.uses.id, fx.s1.id).state == "unsupported"


def test_accept_in_s1_leaves_s2_unreviewed(fx: Fx) -> None:
    fx.w.claim(fx.uses, fx.d)
    fx.w.accept(fx.uses, fx.s1)
    r = fx.w.build()
    assert edge_state(r, fx.uses.id, fx.s1.id).state == "accepted"
    assert edge_state(r, fx.uses.id, fx.s2.id).state == "unreviewed"


def test_reingest_supersedes_old_claims_and_flags_support_lost(fx: Fx) -> None:
    fx.w.claim(fx.impl, fx.d)
    fx.w.accept(fx.impl, None)
    before = fx.w.build()
    v_before = verdict(before, fx.impl.id, fx.s1.id)
    fx.w.new_version(fx.d)  # v2 carries no matching claim
    after = fx.w.build()
    st = edge_state(after, fx.impl.id, fx.s1.id)
    assert (st.state, st.flags) == ("accepted", ("SUPPORT_LOST",))
    assert verdict(after, fx.impl.id, fx.s1.id) == v_before


def test_supersession_keeps_old_locators_and_claims(fx: Fx) -> None:
    fx.w.claim(fx.impl, fx.d)
    before = fx.w.build()
    fx.w.new_version(fx.d)
    after = fx.w.build()
    assert after.claims == before.claims
    assert after.locators == before.locators


def test_unscoped_rel_before_only_claim_unsupported_in_after(fx: Fx) -> None:
    fx.w.claim(fx.impl, fx.e1)
    r = fx.w.build()
    assert edge_state(r, fx.impl.id, fx.s1.id).state == "unreviewed"
    assert edge_state(r, fx.impl.id, fx.s2.id).state == "unsupported"


def test_unscoped_accept_holds_in_every_snapshot_with_support_lost(fx: Fx) -> None:
    fx.w.claim(fx.impl, fx.e1)
    fx.w.accept(fx.impl, None)
    r = fx.w.build()
    assert edge_state(r, fx.impl.id, fx.s1.id).flags == ()
    st = edge_state(r, fx.impl.id, fx.s2.id)
    assert (st.state, st.flags) == ("accepted", ("SUPPORT_LOST",))


def test_rejected_and_superseded_verdicts_win_over_claims(fx: Fx) -> None:
    fx.w.claim(fx.uses, fx.d)
    fx.w.claim(fx.impl, fx.d)
    other = fx.w.rel("uses", fx.a, fx.c)
    fx.w.reject(fx.uses, fx.s1)
    fx.w.supersede(fx.impl, None, fx.w.rel("implements", fx.a, fx.w.entity("req", "R")))
    r = fx.w.build()
    assert edge_state(r, fx.uses.id, fx.s1.id).state == "rejected"
    assert edge_state(r, fx.impl.id, fx.s1.id).state == "superseded"
    assert edge_state(r, other.id, fx.s1.id).state == "unsupported"


def test_successor_excluded_flag(fx: Fx) -> None:
    succ = fx.w.rel("uses", fx.a, fx.c)
    fx.w.supersede(fx.uses, fx.s1, succ)
    assert edge_state(fx.w.build(), fx.uses.id, fx.s1.id).flags == ()
    fx.w.reject(succ, fx.s2)  # rejected only in S2: no flag in S1
    assert edge_state(fx.w.build(), fx.uses.id, fx.s1.id).flags == ()
    fx.w.reject(succ, fx.s1)
    st = edge_state(fx.w.build(), fx.uses.id, fx.s1.id)
    assert (st.state, st.flags) == ("superseded", ("SUCCESSOR_EXCLUDED",))


def test_edge_state_rejects_snapshot_of_other_profile(fx: Fx) -> None:
    other = fx.w.snapshot("x", profile="ukg_pro_wfm")
    with pytest.raises(ValueError, match="profile"):
        edge_state(fx.w.build(), fx.uses.id, other.id)


def test_live_claim_ids_are_listed(fx: Fx) -> None:
    c = fx.w.claim(fx.uses, fx.d)
    r = fx.w.build()
    assert edge_state(r, fx.uses.id, fx.s1.id).live_claim_ids == (c.id,)


@settings(max_examples=200, deadline=None)
@given(worlds())
def test_no_verdict_means_unreviewed_or_unsupported(r: Records) -> None:
    for rel in r.relationships:
        for s in r.snapshots:
            if verdict(r, rel.id, s.id) is not None:
                continue
            has_present = any(c.polarity == "present" for c in live_claims(r, rel.id, s.id))
            expected = "unreviewed" if has_present else "unsupported"
            assert edge_state(r, rel.id, s.id).state == expected
