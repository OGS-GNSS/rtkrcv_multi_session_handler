# RTK Multi-Session Handler

**RTK Multi-Session Handler** è un orchestratore Python progettato per ottenere **posizioni GNSS precise** (con accuratezza centimetrica) di più ricevitori **rover**, utilizzando un **ricevitore master** come riferimento.
Il programma coordina automaticamente le sessioni RTK (Real-Time Kinematic), gestendo lo stream NMEA del master, l’elaborazione dei rover tramite `rtkrcv` (di RTKLIB) e la scrittura dei risultati in un file di configurazione YAML.

## Requisiti

Per il corretto funzionamento è necessario:

1. **Python 3.7 o superiore**
2. **RTKLIB** (compilata con il binario `rtkrcv`)
3. Una rete TCP/IP che permetta la comunicazione tra i ricevitori

### Compilazione RTKRCV

```bash
git clone --recurse-submodules [repository_url]
cd rtklib/app/rtkrcv
make
mkdir -p ../../../lib
cp rtkrcv ../../../lib/
```

Il binario `rtkrcv` deve trovarsi in `./lib/rtkrcv`.

## Utilizzo

```bash
python main.py
```

Il programma:

1. Legge la configurazione dei ricevitori da `list.yaml`
2. Acquisisce la posizione del **Master** tramite stream NMEA
3. Lancia processi `rtkrcv` per ogni **Rover** per calcolare posizioni precise
4. Aggiorna automaticamente le coordinate nel file YAML

## Documentazione Completa

Per tutti i dettagli su configurazione, architettura e troubleshooting, consulta il file:
👉 **[DOCUMENTATION.md](DOCUMENTATION.md)**
