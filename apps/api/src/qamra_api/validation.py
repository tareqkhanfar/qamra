"""Shared input checks."""

import re

PHONE = re.compile(r"^\+?[0-9 ()-]{7,20}$")
