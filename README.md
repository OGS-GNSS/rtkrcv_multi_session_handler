# RTK Multi-Session Handler

**RTK Multi-Session Handler** è un orchestratore Python progettato per automatizzare l'acquisizione di **posizioni GNSS precise** (accuratezza centimetrica) da più ricevitori distribuiti, utilizzando la tecnica RTK (Real-Time Kinematic).

Il sistema gestisce automaticamente:
*   Acquisizione posizione del **Master** (reference station)
*   Coordinamento sessioni RTK per i **Rover**
*   Generazione output **KML** per visualizzazione su Google Earth
*   Interfaccia Web per controllo e monitoraggio in tempo reale

---

## 🚀 Quick Start con Docker

Il modo più semplice e veloce per utilizzare l'applicazione è attraverso Docker.

### Prerequisiti
*   **Docker** installato sulla macchina host.

### Avvio
Esegui il seguente comando nel terminale:

```bash
docker run -p 5000:5000 sgalvi/rtkrcv-multisession:v1
```

Una volta avviato il container, l'applicazione sarà accessibile via browser.

---

## 🖥️ Interfaccia Web

Apri il browser all'indirizzo **[http://localhost:5000](http://localhost:5000)**.

Dalla dashboard potrai:
1.  **Configurare le Stazioni**: Aggiungere, rimuovere e modificare i parametri dei ricevitori (Master/Rover) tramite un editor visuale integrato.
2.  **Controllare il Processo**: Avviare e fermare l'elaborazione con un click.
3.  **Monitorare in Real-Time**: Visualizzare i log di stato e il progresso delle soluzioni (FIX/FLOAT) nel terminale integrato.
4.  **Mappa Interattiva**: Visualizzare istantaneamente le posizioni acquisite su mappa.
5.  **Export Dati**: Scaricare i file KML generati direttamente dall'interfaccia.

> ℹ️ **Nota**: La configurazione viene salvata automaticamente nel file `stations.yaml`.

---

## 🛠️ Installazione Manuale

Se preferisci eseguire l'applicazione nativamente (es. per sviluppo):

### Requisiti
*   **Python 3.7+**
*   **RTKLIB** (con binario `rtkrcv` compilato)
*   Accesso di rete ai ricevitori GNSS

### Setup
1.  Clona il repository con i sottomoduli:
    ```bash
    git clone --recurse-submodules <repository_url>
    ```
2.  Compila RTKLIB:
    ```bash
    cd RTKLIB/app/consapp/rtkrcv/gcc/ && make
    mv rtkrcv /project_path/rtklib/
    rm -r RTKLIB
    ```
3.  Installa le dipendenze Python:
    ```bash
    pip install -r requirements.txt
    ```
4.  Avvia l'interfaccia web:
    ```bash
    python app.py
    ```

---

## 📚 Documentazione

Per una guida dettagliata su:
*   Configurazione avanzata dei ricevitori (`stations.yaml`)
*   Dettagli sull'architettura del sistema
*   Risoluzione problemi (Troubleshooting)
*   Specifiche API

Consulta la documentazione completa:

👉 **[DOCUMENTATION.md](DOCUMENTATION.md)**
