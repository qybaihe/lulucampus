"""Replay 林予安's campus timeline from the repo fixture."""

from pathlib import Path

from portrait_evolve.cli import _replay

if __name__ == "__main__":
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "linyuan_timeline.json"
    raise SystemExit(_replay(fixture, as_json=False))
