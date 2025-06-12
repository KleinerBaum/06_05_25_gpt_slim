"""Utility to obtain the OpenAI model instance used across the app."""

from models.openai_model import OpenAIModel


def get_model() -> OpenAIModel:
    """Return the default OpenAI model."""
    return OpenAIModel()
