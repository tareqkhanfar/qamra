"""Queue names. Workers listen in this priority order."""

GENERATION = "generation"  # character sheets, companions, stories, pages (Phase 2)
PDF = "pdf"  # print files (Phase 2)
MAINTENANCE = "maintenance"  # privacy cleanup, housekeeping
DEFAULT = "default"

ALL = (GENERATION, PDF, MAINTENANCE, DEFAULT)
