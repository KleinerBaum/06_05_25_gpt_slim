def generate_job_ad(tasks, hardskills, softskills, benefits, persona, model):
    prompt = f"""Erstelle eine ansprechende Stellenanzeige:\n\nAufgaben: {tasks}\nHard Skills: {hardskills}\nSoft Skills: {softskills}\nBenefits: {benefits}\nTon/Zielgruppe: {persona}\n"""
    return model.generate(prompt)
