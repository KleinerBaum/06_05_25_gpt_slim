from functions.parse_utils import parse_bullet_list

def extract_hardskills(text: str, model):
    raw = model.generate(f"Extrahiere Hard Skills als Bullet‑List:\n\n{text}")
    return parse_bullet_list(raw)

def extract_softskills(text: str, model):
    raw = model.generate(f"Extrahiere Soft Skills als Bullet‑List:\n\n{text}")
    return parse_bullet_list(raw)
