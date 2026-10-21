"""The coloring scenes of the drawn books; importing this package registers every scene."""

from qamra_workbook.coloring.scenes import palestine, ramadan  # noqa: F401
from qamra_workbook.coloring.scenes.registry import SCENE_H, SCENE_W, SCENES, Scene, framed, get, scene

__all__ = ["SCENES", "SCENE_H", "SCENE_W", "Scene", "framed", "get", "scene"]
