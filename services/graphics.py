"""Image generation helpers using the ACE image service."""

from __future__ import annotations

from typing import List

from ace_tools import image_gen  # type: ignore


def gen_standortkarte(address: str) -> str:
    """Return an image ID for a company location map."""
    prompt = (
        f"Minimalistic flat-design map showing the location of {address} "
        "with a pin, corporate-blue accent, white background"
    )
    result = image_gen.text2im(
        {
            "prompt": prompt,
            "size": "1024x1024",
            "n": 1,
            "transparent_background": False,
        }
    )
    return result["image_ids"][0]


def gen_timeline_graphic(steps: List[str]) -> str:
    """Return an image ID visualising the recruitment timeline."""
    steps_str = ", ".join(steps)
    prompt = (
        "Horizontal timeline infographic, sleek style, showing stages: "
        f"{steps_str}. Corporate colours, plenty of whitespace."
    )
    result = image_gen.text2im(
        {
            "prompt": prompt,
            "size": "1024x512",
            "n": 1,
            "transparent_background": False,
        }
    )
    return result["image_ids"][0]
