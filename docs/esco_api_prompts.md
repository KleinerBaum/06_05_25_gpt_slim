# ESCO API Prompt Templates

Diese Sammlung bietet 30 Beispiel-Prompts zur Verwendung der ESCO API innerhalb des Vacalyser-Projekts. Sie sind in drei Kategorien gegliedert.

## A. ESCO-API über das Agenten-Netzwerk
1. **Jobtitel → Skills abrufen**
   - "Rufe alle relevanten Skills für den Jobtitel ‘Data Scientist’ über die ESCO-API ab."
2. **Skills für eine Berufsbezeichnung**
   - "Suche in der ESCO-API nach den wichtigsten Skills für die Berufsbezeichnung ‘IT Consultant’ und liste sie tabellarisch auf."
3. **Berufsspezifische Qualifikationen**
   - "Welche Qualifikationen sind laut ESCO-API typisch für die Rolle ‘Softwareentwickler’?"
4. **Skill-Beschreibungen für eine Liste von Skills**
   - "Hole mir die Beschreibungen für die Skills ‘Python’, ‘Datenanalyse’ und ‘Machine Learning’ via ESCO-API."
5. **Skills zu Job-ID**
   - "Für die ESCO Job-ID ‘12345’ – gib mir alle verknüpften Skills aus."
6. **Berufe zu einem Skill finden**
   - "Suche alle Berufe, die in der ESCO-API mit dem Skill ‘Teamwork’ verknüpft sind."
7. **Skill Hierarchie anzeigen**
   - "Zeige die übergeordneten und untergeordneten Skills zu ‘Project management’ in ESCO."
8. **Synonyme für Skills**
   - "Finde Synonyme für den Skill ‘Customer Service’ mit der ESCO-API."
9. **Alle Skills eines Berufsfelds**
   - "List alle Skills, die im Berufsfeld ‘Digital Marketing’ laut ESCO benötigt werden."
10. **Sprachen eines Berufs**
    - "Welche Sprachkenntnisse werden für ‘Kundenbetreuer’ laut ESCO empfohlen?"
11. **Skill-Gruppen für einen Beruf**
    - "Gruppiere alle Skills für ‘Buchhalter’ nach Skill-Typ gemäß ESCO."
12. **Skill Level abfragen**
    - "Welches Skill-Level empfiehlt ESCO für ‘Python’ im Job ‘Data Analyst’?"
13. **Typische Aufgaben eines Berufs**
    - "Zeige alle typischen Aufgaben für den Beruf ‘Personalreferent’ gemäß ESCO."
14. **Vergleich zweier Jobs**
    - "Vergleiche die geforderten Skills für ‘Frontend Developer’ und ‘Backend Developer’ mit der ESCO-API."
15. **Job-Übersetzung (DE/EN)**
    - "Übersetze den deutschen Jobtitel ‘Vertriebsleiter’ ins Englische und ermittle die zugehörigen ESCO-Skills."
16. **Neue Skills seit X Tagen**
    - "Liste Skills, die in den letzten 30 Tagen neu in die ESCO-API aufgenommen wurden."
17. **Qualifikationen zu Skill**
    - "Welche formalen Qualifikationen verlangt ESCO für den Skill ‘Cyber Security’?"
18. **Skill-IDs in Text einbauen**
    - "Kennzeichne in folgendem Text alle Skills mit ihrer ESCO-ID: ‘Kenntnisse in Java, Python und Datenbanken.’"
19. **Skill-Gap-Analyse**
    - "Führe eine Skill-Gap-Analyse für den Lebenslauf [Text] mit ESCO-Skills für ‘Projektmanager’ durch."
20. **Berufsbezeichnungen nach Branche**
    - "Welche Jobtitel sind in der Branche ‘Gesundheitswesen’ in ESCO gelistet?"

## B. Lokale Shell-Kommandos kombinieren
21. **API-Resultat speichern** –
    "Speichere das ESCO-API-Resultat als ‘skills.json’ im Arbeitsverzeichnis per Shell-Befehl."
22. **Skill-Liste als CSV exportieren** –
    "Konvertiere die abgefragte Skill-Liste in eine CSV-Datei und speichere sie lokal via Shell."
23. **Skill-Suche & Vorverarbeitung** –
    "Führe eine Skill-Suche via ESCO-API durch und filtere die Top 5 Ergebnisse mit einem lokalen Python-Skript."
24. **Automatisierter Abgleich Lebenslauf – ESCO** –
    "Extrahiere Skills aus diesem Lebenslauf und prüfe sie automatisiert mit ESCO-Skills via Shell-Tool."
25. **Lokales Python-Skript für Batch-API-Calls** –
    "Starte das lokale Python-Skript ‘fetch_esco_skills.py’ mit dem Parameter ‘Data Engineer’ via Shell."
26. **Skill-Visualisierung** –
    "Erzeuge eine Skill-Mindmap aus den ESCO-API-Daten und öffne die HTML-Ausgabe per Shell."
27. **API-Resultat zippen** –
    "Packe alle erstellten ESCO-API-Resultate in ein ZIP-Archiv via Shell-Befehl."
28. **Shell-Ausgabe zurückgeben** –
    "Zeige das Ergebnis des Shell-Kommandos ‘ls -lh skills*’."
29. **Logfile prüfen** –
    "Führe ‘cat esco_api.log | tail -n 20’ per Shell aus, um die letzten 20 Logzeilen anzuzeigen."
30. **Abhängigkeiten installieren** –
    "Installiere alle notwendigen Python-Abhängigkeiten (‘requests’, ‘pandas’) via Shell für die ESCO-Integration."

## C. Beispiel-Prompts für Streamlit-Integration
```python
# Prompt für die Funktion
prompt = (
    "Hole alle Skills für den Jobtitel ‘Data Scientist’ von der ESCO-API. "
    "Zeige sie als auswählbare Checkbox-Liste im Streamlit-Interface."
)
```

```python
# Dynamische Abfrage und Anzeige in Streamlit
prompt = (
    "Führe eine Skill-Suche in ESCO für ‘IT-Projektmanager’ durch und stelle das Ergebnis "
    "in einer Streamlit-Selectbox zur Auswahl bereit."
)
```
