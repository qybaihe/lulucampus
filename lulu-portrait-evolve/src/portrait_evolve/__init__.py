"""噜噜自进化画像：用每一次平台行为校准、永不过时的用户画像。"""

from portrait_evolve.engine import IngestResult, LivingPortraitEngine
from portrait_evolve.events import BehaviorEvent
from portrait_evolve.explain import explain
from portrait_evolve.portrait import Portrait
from portrait_evolve.store import PortraitStore

__all__ = [
    "BehaviorEvent",
    "IngestResult",
    "LivingPortraitEngine",
    "Portrait",
    "PortraitStore",
    "explain",
]
__version__ = "0.1.0"
