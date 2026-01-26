Obiettivo: Visualizzare il risultato geografico.
Procedura:
1. Al termine del processo main.py (exit code 0), scansiona la cartella output/.
2. Trova il file .kml più recente.
3. Converti o parsa il KML per estrarre le coordinate (o usalo direttamente se la lib supporta KML).
4. Mostra una mappa OpenStreetMap (usando Leaflet.js) in testa alla dashboard.
5. Plotta il percorso/punti estratti sulla mappa.