# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
from tests.domain.builders import World


def test_minimal_world_builds(world: World) -> None:
    s1, s2 = world.snapshot("s1"), world.snapshot("s2")
    e1, e2, _design = world.export(s1), world.export(s2), world.design()
    a, b = world.entity("cfg", "A"), world.entity("cfg", "B")
    uses = world.rel("uses", a, b)
    world.claim(uses, e1)
    world.claim(uses, e2)
    r = world.build()
    assert len(r.claims) == 2
    assert len(r.relationships) == 1
