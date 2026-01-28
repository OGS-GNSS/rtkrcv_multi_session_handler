# RTK Multi-Session Handler


**RTK Multi-Session Handler** è un orchestratore Python progettato per ottenere **posizioni GNSS precise** (accuratezza centimetrica) da più ricevitori **rover**, utilizzando un **ricevitore master** come riferimento.
Il programma coordina automaticamente le sessioni RTK (Real-Time Kinematic), gestendo lo stream NMEA del master, l’elaborazione dei rover tramite `rtkrcv` (di RTKLIB) e la scrittura dei risultati in un file di configurazione YAML.

--- 

## 🐳 Quick Start con Docker.

Il modo più semplice per avviare l'applicazione senza installare dipendenze è usare Docker.

### Prerequisiti
* Docker installato sulla macchina.

### Avvio rapido
Esegui questo comando nel terminale:

```bash
docker run -p 5000:5000 --restart unless-stopped sgalvi/rtkrcv-multisession:latest
```

---

## Installazione manuale

### Requisiti

Per il corretto funzionamento è necessario:

1. **Python 3.7 o superiore**
2. **RTKLIB** (con il binario `rtkrcv` compilato)
3. Una rete TCP/IP che permetta la comunicazione tra i ricevitori

---

### Installazione

#### Compilare RTKRCV

```bash
git clone --recurse-submodules [repository_url]
cd rtklib/app/rtkrcv
make
mkdir -p ../../../lib
cp rtkrcv ../../../lib/
```

Il binario `rtkrcv` deve trovarsi in `./lib/rtkrcv`.

### 2️⃣ Installare le dipendenze Python

Dal percorso principale del progetto:

```bash
pip install -r requirements.txt
```

---

## Utilizzo

Eseguire:

```bash
python main.py
```

Il programma:

1. Legge la configurazione dei ricevitori da `stations.yaml`
2. Acquisisce la posizione del **Master** tramite stream NMEA
3. Lancia processi `rtkrcv` per ogni **Rover** per calcolare le posizioni precise
4. Genera automaticamente un file KML nella directory `output/`

---

## Interfaccia Web

Per avviare l'interfaccia web eseguire:

```bash
python app.py
```

a questo punto collegarsi con un browser a `http://localhost:5000`
da qui potremo aggiungere/rimuovere/configurare le stazioni ed avviare il processo 

---

## Documentazione Completa

Per dettagli su:

* configurazione dei ricevitori
* formati dei file YAML
* architettura del sistema
* troubleshooting

consulta -> **[DOCUMENTATION.md](DOCUMENTATION.md)**

