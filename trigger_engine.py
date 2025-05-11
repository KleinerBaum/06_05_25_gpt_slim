# trigger_engine.py
# ─────────────────────────────────────────────────────────────────────────────
"""Dependency graph engine for Vacalyzer dynamic field updates (pure Python)."""

from __future__ import annotations
from typing import Callable, Iterable
import networkx as nx

class TriggerEngine:
    """DAG of field dependencies and associated processors for auto-updates."""
    def __init__(self) -> None:
        self.graph: nx.DiGraph = nx.DiGraph()
        self._processors: dict[str, Callable[[dict], None]] = {}

    # Graph construction methods
    def register_node(self, key: str) -> None:
        if key not in self.graph:
            self.graph.add_node(key)

    def register_dependency(self, source: str, target: str) -> None:
        """Declare that *target* depends on *source* (directed edge source->target)."""
        self.register_node(source)
        self.register_node(target)
        self.graph.add_edge(source, target)

    def register_dependencies(self, pairs: Iterable[tuple[str, str]]) -> None:
        for src, tgt in pairs:
            self.register_dependency(src, tgt)

    # Processor registration
    def register_processor(self, key: str, func: Callable[[dict], None]) -> None:
        """Attach a processor function that recomputes *key*."""
        self._processors[key] = func

    # Runtime notification
    def notify_change(self, updated_key: str, state: dict) -> None:
        """Invoke all processors affected by a change in *updated_key*."""
        if updated_key not in self.graph:
            return  # no dependencies
        affected = nx.descendants(self.graph, updated_key)
        if not affected:
            return
        # Process in topological order to respect dependency chains
        for node in nx.topological_sort(self.graph):
            if node in affected:
                processor = self._processors.get(node)
                if processor:
                    processor(state)

# Default dependency pairs (edges: A -> B means B updates when A changes)
_DEPENDENCY_PAIRS: list[tuple[str, str]] = [
    # Auto-suggestions and dynamic computations
    ("job_title", "task_list"),               # Job title triggers task suggestions
    ("industry_experience", "task_list"),     # Industry context refines tasks
    ("task_list", "must_have_skills"),        # Tasks influence must-have skills
    ("must_have_skills", "nice_to_have_skills"),  # Must-haves lead to nice-to-haves
    ("task_list", "salary_range"),            # Role scope influences salary
    ("must_have_skills", "salary_range"),     # Required skills influence salary
    ("parsed_data_raw", "salary_range"),      # Initial parse triggers salary estimate
    ("remote_work_policy", "desired_publication_channels"),  # Remote affects channels
    ("job_level", "bonus_scheme"),            # Seniority may entail bonus
    ("job_title", "commission_structure"),    # Sales roles get commission structure
    ("language_requirements", "translation_required")  # Language needs affect translation
]

def build_default_graph(engine: TriggerEngine) -> None:
    """Populate the TriggerEngine with the standard Vacalyser dependency graph."""
    engine.register_dependencies(_DEPENDENCY_PAIRS)
