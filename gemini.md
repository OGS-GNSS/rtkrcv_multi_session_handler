# Antigravity Setup & Context

**Project Goal**: Creare una Dashboard Web (GUI) per l'orchestratore GNSS esistente.
**Tech Stack**: Python (Flask), HTML/CSS (Bootstrap o Tailwind), JavaScript (Leaflet.js per mappe), YAML parser.

## Architecture: DOE Framework [2]

1.  **Directives (D)**: Le SOP in `directives/` definiscono le regole di business.
2.  **Orchestration (O)**: L'LLM legge le direttive e coordina il lavoro.
3.  **Execution (E)**: Script Python deterministici.
    *   **CORE**: Il nucleo esistente (`main.py`, `rtkrcv`) NON deve essere riscritto, solo invocato.
    *   **NEW**: Il server Flask (`app.py`) gestisce l'interfaccia e l'I/O.

## Operating Principles [5]
*   **Self-Correction**: Se il server Flask crasha o il parsing YAML fallisce, leggi i log e correggi il codice.
*   **Deterministic Core**: Non modificare la logica di calcolo GNSS. La GUI è solo un "telecomando" per `main.py`.
