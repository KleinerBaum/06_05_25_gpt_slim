import random

def predict_salary(job_title: str, combined_skills, model=None):
    base = random.randint(40, 60) * 1000
    spread = random.randint(5, 15) * 1000
    return {"min": base, "max": base + spread, "currency": "EUR"}
