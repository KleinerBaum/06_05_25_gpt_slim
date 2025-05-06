from functions.parse_utils import parse_bullet_list

def extract_tasks(text: str, model):
    raw = model.generate(f"Extrahiere Aufgaben (max 10) als Bullet‑List:\n\n{text}")
    return parse_bullet_list(raw)[:10]
