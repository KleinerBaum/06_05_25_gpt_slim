"""Utility to register custom tool functions for OpenAI function calling.

Originally from `src/utils/tool_registry.py`.


Zentrale Sammlung aller @tool-dekorierten Funktionen.

• @tool(...) registriert eine Funktion samt OpenAI-Schema
• list_openai_functions() liefert die Schemaliste für ChatCompletion
"""

from __future__ import annotations
from typing import Callable, Dict, List

# Interner Speicher
_TOOL_REGISTRY: Dict[str, dict] = {}  # name -> schema
_FUNC_REGISTRY: Dict[str, Callable] = {}  # name -> echte Py-Funktion


def tool(
    *,
    name: str,
    description: str,
    parameters: dict | None = None,
    return_type: str | None = None,
):
    """Decorator zum Registrieren einer Tool-Funktion."""

    def decorator(func: Callable):
        schema = {
            "name": name,
            "description": description,
            "parameters": parameters
            or {"type": "object", "properties": {}, "required": []},
        }
        if return_type:
            schema["returns"] = return_type
        _TOOL_REGISTRY[name] = schema
        _FUNC_REGISTRY[name] = func
        return func

    return decorator


def list_openai_functions() -> List[dict]:
    """Gibt alle registrierten Schemas (OpenAI-kompatibel) als Liste zurück."""
    return list(_TOOL_REGISTRY.values())


def get_function(name: str) -> Callable | None:
    """Liefert die echte Python-Funktion zum Tool-Namen."""
    return _FUNC_REGISTRY.get(name)
