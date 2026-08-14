"""噜噜自进化画像：层次先验 × 行为证据累积 × 滞回稳态。"""

from portrait_evolve.affinity import score_pair
from portrait_evolve.engine import IngestResult, LivingPortraitEngine
from portrait_evolve.events import BehaviorEvent
from portrait_evolve.explain import explain
from portrait_evolve.models import model_card
from portrait_evolve.portrait import Portrait
from portrait_evolve.report import build_report
from portrait_evolve.store import PortraitStore

__all__ = [
    "BehaviorEvent",
    "IngestResult",
    "LivingPortraitEngine",
    "Portrait",
    "PortraitStore",
    "build_report",
    "explain",
    "model_card",
    "score_pair",
]
__version__ = "0.2.0"
