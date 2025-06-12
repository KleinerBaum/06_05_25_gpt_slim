from __future__ import annotations
from typing import Any

def update_publication_channels(state: dict[str, Any]) -> None:
    """Empfiehlt Veröffentlichungsplattformen basierend auf der Remote-Arbeitsregelung (überschreibt keine Nutzereingabe)."""
    # Falls Nutzer bereits Kanäle angegeben hat, nicht überschreiben
    if state.get("desired_publication_channels"):
        return
    raw_policy = state.get("remote_work_policy", "")
    if isinstance(raw_policy, (list, tuple)):
        remote = " ".join(str(val).strip().lower() for val in raw_policy)
    else:
        remote = str(raw_policy).strip().lower()
    if remote in {"hybrid", "full remote"}:
        state["desired_publication_channels"] = "LinkedIn Remote Jobs; WeWorkRemotely"
