from __future__ import annotations
from typing import Callable, Iterable, Set
import networkx as nx

__all__ = ["TriggerEngine", "build_default_graph"]


class TriggerEngine:
    """Directed acyclic graph managing field dependencies and processors."""

    def __init__(self) -> None:
        """Initialize an empty dependency graph."""
        self.graph: nx.DiGraph = nx.DiGraph()
        self._processors: dict[str, Callable[[dict], None]] = {}

    def register_node(self, key: str) -> None:
        """Ensure ``key`` exists as a node in the graph."""
        if key not in self.graph:
            self.graph.add_node(key)

    def register_dependency(self, source: str, target: str) -> None:
        """Declare that ``target`` depends on ``source``.

        Args:
            source: Source node key.
            target: Target node key.
        """
        self.register_node(source)
        self.register_node(target)
        self.graph.add_edge(source, target)

    def register_dependencies(self, pairs: Iterable[tuple[str, str]]) -> None:
        """Register multiple dependency pairs.

        Args:
            pairs: Iterable of ``(source, target)`` tuples.
        """
        for src, tgt in pairs:
            self.register_dependency(src, tgt)

    def register_processor(self, key: str, func: Callable[[dict], None]) -> None:
        """Attach a processor function for ``key``.

        Args:
            key: Node key the processor updates.
            func: Function that mutates the state when ``key`` changes.
        """
        self._processors[key] = func

    def notify_change(self, updated_key: str, state: dict) -> None:
        """Run processors for nodes affected by ``updated_key``.

        Args:
            updated_key: The key that has changed.
            state: Current state dictionary passed to processors.
        """
        if updated_key not in self.graph:
            return
        affected: Set[str] = nx.descendants(self.graph, updated_key)
        for node in affected:
            processor = self._processors.get(node)
            if processor:
                processor(state)


# Definierte Abhängigkeiten zwischen den Wizard-Feldern
_DEPENDENCY_PAIRS: list[tuple[str, str]] = [
    # Wenn Jobtitel/Firmendaten geändert -> Aufgaben & Skills aktualisieren
    ("job_title", "task_list"),
    ("job_title", "must_have_skills"),
    ("job_title", "commission_structure"),
    ("job_level", "bonus_scheme"),
    # Aufgaben/Muss-Fähigkeiten ändern -> Gehaltsspanne aktualisieren
    ("task_list", "salary_range"),
    ("must_have_skills", "salary_range"),
    ("must_have_skills", "nice_to_have_skills"),
    # Remote-Policy ändern -> empfohlene Publikationskanäle aktualisieren
    ("remote_work_policy", "desired_publication_channels"),
    # Branchen-Erfahrung ändern -> Aufgabenliste aktualisieren
    ("industry_experience", "task_list"),
    # Rohtext geändert (z.B. aus Datei-Analyse) -> Gehaltsspanne verfeinern (wenn 'competitive')
    ("parsed_data_raw", "salary_range"),
]


def build_default_graph(engine: TriggerEngine) -> None:
    """Populate ``engine`` with default dependencies and processors.

    Args:
        engine: The :class:`TriggerEngine` instance to configure.

    Returns:
        None.
    """
    engine.register_dependencies(_DEPENDENCY_PAIRS)
    # Alle Prozessorfunktionen zentral registrieren
    from logic.processors import register_all_processors

    register_all_processors(engine)
