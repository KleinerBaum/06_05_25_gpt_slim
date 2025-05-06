from functions.parse_utils import parse_bullet_list

def extract_benefits(text: str, model):
    raw = model.generate(f"Liste Benefits als Bullet‑List:\n\n{text}")
    return parse_bullet_list(raw)
