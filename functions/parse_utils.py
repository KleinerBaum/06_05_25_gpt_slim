import re
from typing import List

def parse_bullet_list(raw: str) -> List[str]:
    items = []
    for line in raw.splitlines():
        if re.match(r"^[-•]\s?", line.strip()):
            items.append(re.sub(r"^[-•]\s?", "", line.strip()))
    return items or [raw.strip()]
