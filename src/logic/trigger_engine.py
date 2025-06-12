from __future__ import annotations
from typing import Callable, Iterable, Set
import networkx as nx

__all__ = ["TriggerEngine", "build_default_graph"]

class TriggerEngine:
    """DAG zur Verwaltung von Feldabhängigkeiten und zugehörigen Verarbeitungsfunktionen."""
    def __init__(self) -> None:
        self.graph: nx.DiGraph = nx.DiGraph()
        self._processors: dict[str, Callable[[dict], None]] = {}

    def register_node(self, key: str) -> None:
        if key not in self.graph:
            self.graph.add_node(key)

    def register_dependency(self, source: str, target: str) -> None:
        """Deklariert, dass *target* von *source* abhängt (Kante source→target)."""
        self.register_node(source)
        self.register_node(target)
        self.graph.add_edge(source, target)

    def register_dependencies(self, pairs: Iterable[tuple[str, str]]) -> None:
        for src, tgt in pairs:
            self.register_dependency(src, tgt)

    def register_processor(self, key: str, func: Callable[[dict], None]) -> None:
        """Registriert eine Verarbeitungsfunktion, die ausgeführt wird, wenn *key* neu berechnet werden muss."""
        self._processors[key] = func

    def notify_change(self, updated_key: str, state: dict) -> None:
        """Benachrichtigt die Engine, dass sich *updated_key* geändert hat, und führt alle abhängigen Verarbeiter aus."""
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
    ("parsed_data_raw", "salary_range")
]

def build_default_graph(engine: TriggerEngine) -> None:
    """Befüllt die TriggerEngine mit dem Abhängigkeitsgraphen und registriert die Verarbeitungsfunktionen."""
    engine.register_dependencies(_DEPENDENCY_PAIRS)
    # Importiere Verarbeitungsfunktionen aus Prozessor-Modulen
    from src.processors.salary import update_salary_range
    from src.processors.publication import update_publication_channels

    # Aufgaben-, Skill- und Benefit-Funktionen aus dem Logic-Paket importieren
    from src.logic.processors import (
        update_task_list,
        update_must_have_skills,
        update_nice_to_have_skills,
        update_bonus_scheme,
        update_commission_structure,
    )
    # Funktionen mit ihren Ziel-Feldern verknüpfen
    engine.register_processor("task_list", update_task_list)
    engine.register_processor("must_have_skills", update_must_have_skills)
    engine.register_processor("nice_to_have_skills", update_nice_to_have_skills)
    engine.register_processor("salary_range", update_salary_range)
    engine.register_processor("desired_publication_channels", update_publication_channels)
    engine.register_processor("bonus_scheme", update_bonus_scheme)
    engine.register_processor("commission_structure", update_commission_structure)
