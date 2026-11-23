# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 Darshan U Shetty and contributors
"""PDF to word locators and page fragments. pdfplumber runs only in the sandbox child."""

import importlib
import sys

# Planted-bug target: a top-level `import pdfplumber` here would load it in the parent.
_ = (importlib, sys)
