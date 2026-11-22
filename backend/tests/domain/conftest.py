# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
import pytest

from tests.domain.builders import World


@pytest.fixture
def world() -> World:
    return World()
