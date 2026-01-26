# RTK Multi-Session Handler - Documentazione Completa

## Indice
1. [Panoramica](#panoramica)
2. [Architettura del Sistema](#architettura-del-sistema)
3. [Requisiti e Installazione](#requisiti-e-installazione)
4. [Configurazione](#configurazione)
5. [Utilizzo](#utilizzo)
6. [Flusso di Esecuzione](#flusso-di-esecuzione)
7. [Componenti Principali](#componenti-principali)
8. [Struttura dei File](#struttura-dei-file)
9. [File Temporanei e Log](#file-temporanei-e-log)
10. [Gestione degli Errori](#gestione-degli-errori)
11. [Troubleshooting](#troubleshooting)
12. [Limitazioni Note](#limitazioni-note)

---

## Panoramica

**RTK Multi-Session Handler** è un orchestratore Python progettato per automatizzare l'acquisizione di coordinate precise di ricevitori GNSS distribuiti utilizzando la tecnica RTK (Real-Time Kinematic).

### Scopo del Progetto

Il sistema gestisce sessioni multiple di posizionamento RTK coordinando:
- **Receiver Master**: acquisisce la propria posizione assoluta tramite stream NMEA
- **Receiver Rover**: acquisiscono posizioni precise (precisione centimetrica) tramite correzioni differenziali dal Master

### Caratteristiche Principali

- ✅ Gestione automatizzata del workflow completo RTK
- ✅ Configurazione centralizzata in formato YAML
- ✅ Monitoraggio in tempo reale dell'elaborazione RTKRCV
- ✅ Persistenza automatica delle coordinate acquisite
- ✅ Gestione robusta dei processi con timeout
- ✅ Sistema di logging completo per debugging
- ✅ Pulizia automatica dei file temporanei

---

## Architettura del Sistema

### Componenti ad Alto Livello

```
┌─────────────────────────────────────────────────────────┐
│                      RTKManager                         │
│  (Orchestratore principale - coordina il workflow)      │
└───────────────┬────────────────────────┬────────────────┘
                │                        │
        ┌───────▼────────┐      ┌────────▼──────────┐
        │     Master     │      │      Rover        │
        │  (Ricevitore)  │      │   (Ricevitore)    │
        └───────┬────────┘      └────────┬──────────┘
                │                        │
    ┌───────────▼──────────┐  ┌──────────▼────────────┐
    │  NMEA TCP Stream     │  │  RTKRCV Process       │
    │  (Posizione Master)  │  │  (Correzioni RTK)     │
    └──────────────────────┘  └───────────────────────┘
```

### Flusso Dati

1. **Master → NMEA Stream**: Il Master trasmette la propria posizione GNSS via TCP usando protocollo NMEA
2. **Manager → Master**: Estrae coordinate dal messaggio GGA NMEA
3. **Master → RTKRCV**: Le coordinate del Master diventano la base per le correzioni RTK
4. **Rover → RTKRCV**: I Rover ricevono correzioni differenziali e calcolano posizioni precise
5. **RTKRCV → Solution File**: Le coordinate precise vengono scritte su file `.pos`
6. **Manager → Output**: Le coordinate vengono scritte su file KML nella directory `output/`

---

## Requisiti e Installazione

### Dipendenze di Sistema

- **Python 3.x** (versione 3.7 o superiore raccomandata)
- **RTKLIB** (compilato come binario `rtkrcv`)
- **Rete TCP/IP** per comunicazione con receiver GNSS

### Dipendenze Python

```bash
pip install -r requirements.txt
```

Dipendenze:
- `PyYAML` - parsing e scrittura file di configurazione YAML

### Compilazione RTKLIB

Il progetto include RTKLIB come git submodule nella directory `/rtklib/`:

```bash
# Clonare il repository con i submodule
git clone --recurse-submodules [repository_url]

# Oppure inizializzare i submodule dopo il clone
git submodule update --init --recursive

# Compilare RTKRCV (RTKLIB Explorer)
cd rtklib/app/rtkrcv
make

# Copiare il binario nella directory lib/
mkdir -p ../../../lib
cp rtkrcv ../../../lib/
```

Il binario compilato deve trovarsi in `./lib/rtkrcv` (relativo alla root del progetto).

### Verifica Installazione

```bash
# Verifica presenza binario RTKRCV
ls -lh ./lib/rtkrcv

# Test avvio programma
python main.py
```

---

## Configurazione

### File di Configurazione: `stations.yaml`

Il file `stations.yaml` è il file di configurazione centrale che definisce tutti i receiver GNSS da gestire. Il file viene validato all'avvio per garantire la correttezza della struttura.

#### Struttura del File

```yaml
receivers:
  <serial_number>:
    serial: <serial_number>
    ip: <ip_address>
    port: <port_number>
    role: master|rover
    timeout: 300      # Opzionale, default 300s
    # coords: ... (Le coordinate non vengono più salvate qui)
```

#### Esempio Configurazione

```yaml
receivers:
  2409-001:
    serial: 2409-001
    ip: 10.158.0.190
    port: 2222
    role: master
    coords:
      lat: 46.037347
      lon: 13.253102
      alt: 149.258

  2409-002:
    serial: 2409-002
    ip: 10.158.0.163
    port: 2222
    role: rover
```

#### Parametri

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `serial` | String | Identificatore univoco del receiver |
| `ip` | String | Indirizzo IP del receiver sulla rete |
| `port` | Integer | Porta TCP per connessione (tipicamente 2222) |
| `role` | String | Ruolo del receiver: `master` o `rover` |
| `timeout` | Integer | (Opzionale) Timeout in secondi per acquisizione (default: 300) |
| `coords` | Object | Coordinate acquisite (popolato automaticamente) |
| `coords.lat` | Float | Latitudine in gradi decimali |
| `coords.lon` | Float | Longitudine in gradi decimali |
| `coords.alt` | Float | Altitudine ellissoidale in metri |

#### Note sulla Configurazione

- **Un solo Master**: Il sistema supporta un solo receiver Master per sessione
- **Multipli Rover**: È possibile configurare N receiver Rover
- **Coordinate Opzionali**: Se presenti nel file (manualmente), il sistema le usa
- **Output Separato**: I risultati vengono salvati in un file KML separato, non nel YAML

### Configurazione RTKRCV

La configurazione RTKRCV viene generata automaticamente dal template in `utils/rtklib_config.py`.

#### Parametri Principali

- **Modalità**: Kinematic (RTK in movimento)
- **Frequenze**: L1+L2 dual-frequency
- **Sistemi GNSS**: GPS + GLONASS (Galileo e BeiDou disabilitati)
- **Elevazione minima**: 15° (compromesso tra precisione e disponibilità satelliti)
- **Ambiguity Resolution**: Continuous mode con threshold=2.0
- **SNR Mask**: L1=30dBHz, L2/L5=25dBHz
- **Half-cycle detection**: DISABILITATO (previene problemi con satelliti specifici)

#### Satelliti Esclusi

Il template esclude automaticamente satelliti problematici:
- `G46` - GPS PRN 46 (causa half-cycle slips)
- `C50` - BeiDou PRN 50
- `S90`, `S145`, `S150` - SBAS satelliti non necessari

#### Timeout

- **Master**: 30 secondi (acquisizione posizione NMEA)
- **Rover**: 300 secondi (elaborazione RTK fino a fix)

---

## Utilizzo

### Avvio del Sistema

```bash
# Dalla directory root del progetto
python main.py
```

### Output Tipico

```
=== RTK Manager ===

Caricati 2 ricevitori
Acquisizione posizione Master da stream NMEA...
Master posizionato: Lat=46.037347, Lon=13.253102, Alt=149.258
# Output salvato alla fine

Processing Rover 2409-002...
File di configurazione creato: /tmp/rtkrcv_2409-002.conf
Avvio RTKRCV per Rover 2409-002...
Comando: /path/to/lib/rtkrcv -nc -t 2 -o /tmp/rtkrcv_2409-002.conf
RTKRCV avviato in background (PID: 12345)
Attendo inizializzazione RTKRCV e creazione file trace...

✓ File trace trovato: rtkrcv_20250104_153045.trace
--- Monitoraggio RTKRCV (ultime 3 righe aggiornate in tempo reale) ---
2025/01/04 15:30:50 $GNGGA solution: 46.037123,13.253456,148.234 Q=1 ns=12
2025/01/04 15:30:51 $GNGGA solution: 46.037124,13.253457,148.235 Q=1 ns=12
2025/01/04 15:30:52 $GNGGA solution: 46.037125,13.253458,148.236 Q=1 ns=12
Rover 2409-002 posizionato: Lat=46.037124, Lon=13.253457, Alt=148.235
# Output salvato alla fine

=== Processo completato ===
File KML creato: output/output_20250104_153500.kml
Serial: 2409-001, IP: 10.158.0.190, Port: 2222, Role: master | Lat=46.037347, Lon=13.253102, Alt=149.258
Serial: 2409-002, IP: 10.158.0.163, Port: 2222, Role: rover | Lat=46.037124, Lon=13.253457, Alt=148.235
```

### Comportamento del Sistema

1. **Se il Master ha già coordinate**: Salta l'acquisizione NMEA e procede direttamente ai Rover
2. **Se un Rover ha già coordinate**: Le sovrascrive con nuova acquisizione
3. **Elaborazione Sequenziale**: I Rover vengono processati uno alla volta (non in parallelo)
4. **Output KML**: Viene generato un singolo file KML finale nella directory `output/`

---

## Flusso di Esecuzione

### Diagramma di Sequenza

```
main.py
  │
  ├─► RTKManager.__init__()
  │   └─► Inizializza percorsi yaml_path e rtklib_path
  │
  ├─► RTKManager.run()
      │
      ├─► load_receivers()
      │   ├─► Validatore.validate_config()
      │   ├─► Legge stations.yaml
      │   └─► Crea oggetti Master e Rover
      │
      ├─► acquire_master_position() [se necessario]
      │   ├─► Master.read_nmea_position()
      │   │   ├─► Connessione TCP a Master
      │   │   ├─► Ricezione stream NMEA
      │   │   ├─► parse_gga() per estrarre coordinate
      │   │   └─► Imposta coordinate Master
      │   └─► [Nessun salvataggio intermedio]
      │
      └─► process_rovers()
          │
          └─► Per ogni Rover:
              ├─► Rover.process_with_rtkrcv()
              │   │
              │   ├─► generate_rtkrcv_config()
              │   │   └─► Crea file .conf temporaneo
              │   │
              │   ├─► Avvia processo RTKRCV
              │   │   └─► subprocess.Popen() in background
              │   │
              │   ├─► Monitoraggio loop (ogni 1s):
              │   │   ├─► Trova file trace dinamicamente
              │   │   ├─► Legge ultime 3 righe trace
              │   │   ├─► Aggiorna display (ANSI overlay)
              │   │   ├─► Controlla file soluzione
              │   │   └─► Verifica timeout/processo attivo
              │   │
              │   ├─► read_solution_file()
              │   │   ├─► Legge file .pos
              │   │   ├─► Cerca ultima riga con Q=1 (fix)
              │   │   └─► Estrae coordinate
              │   │
              │   ├─► _stop_rtkrcv()
              │   │   ├─► SIGTERM (graceful)
              │   │   └─► SIGKILL se non risponde
              │   │
              │   └─► Cleanup file temporanei
              │       └─► Preserva log se errore
              │
              └─► [Nessun salvataggio intermedio]
```

### Stati del Processo

#### Master
1. **NO_COORDINATES** → Connessione TCP → Parsing NMEA → **POSITIONED**
2. **POSITIONED** → Skip acquisizione

#### Rover
1. **READY** → Genera config → **CONFIG_CREATED**
2. **CONFIG_CREATED** → Avvia RTKRCV → **PROCESSING**
3. **PROCESSING** → Monitora trace → **MONITORING**
4. **MONITORING** → Fix RTK trovato (Q=1) → **FIXED**
5. **MONITORING** → Timeout scaduto → **TIMEOUT**
6. **FIXED** → Cleanup → **COMPLETED**

---

## Componenti Principali

### 1. RTKManager (`manager/rtk_manager.py`)

**Responsabilità**: Orchestratore principale del workflow RTK.

#### Metodi Principali

##### `__init__(yaml_path, rtklib_path)`
Inizializza il manager con i percorsi ai file di configurazione e al binario RTKRCV.

##### `load_receivers()`
Carica la configurazione dei receiver dal file YAML e istanzia oggetti Master/Rover.

**Implementazione**:
```python
for item in data.get('receivers', {}).values():
    if role == 'master':
        self.master = Master(...)
        if 'coords' in item:
            self.master.set_coordinates(...)
    elif role == 'rover':
        rover = Rover(...)
        if 'coords' in item:
            rover.set_coordinates(...)
        self.rovers.append(rover)
```

##### `acquire_master_position()`
Acquisisce la posizione del Master tramite stream NMEA TCP.

**Timeout**: 30 secondi
**Ritorna**: `True` se acquisizione riuscita, `False` altrimenti

##### `process_rovers()`
Elabora sequenzialmente tutti i Rover configurati chiamando `Rover.process_with_rtkrcv()` per ognuno.

##### `save_results()`
Salva le coordinate acquisite in un file KML timestamped nella directory `output/`.

##### `run()`
Punto di ingresso principale che esegue il workflow completo:
1. Carica receiver
2. Acquisisce posizione Master (se necessario)
3. Processa tutti i Rover
4. Stampa riepilogo finale

---

### 2. Ricevitore (`models/receiver.py`)

**Responsabilità**: Classe base per tutti i receiver GNSS.

#### Attributi

- `serial_number`: Identificatore univoco
- `ip_address`: IP del receiver sulla rete
- `port`: Porta TCP per connessione
- `role`: Ruolo (`master` o `rover`)
- `coords`: Oggetto Coordinates (opzionale)
- `running`: Flag stato operativo

#### Metodi

##### `set_coordinates(lat, lon, alt)`
Imposta le coordinate del receiver creando un oggetto `Coordinates`.

##### `get_coordinates()`
Restituisce le coordinate come dizionario `{'lat': ..., 'lon': ..., 'alt': ...}`.

##### `has_coordinates()`
Verifica se le coordinate sono state impostate.

Altri attributi: `sol_status`, `linked_master_id`.

---

### 3. Master (`models/master.py`)

**Responsabilità**: Receiver Master che acquisisce posizione tramite stream NMEA.

#### Metodi

##### `read_nmea_position(timeout=30)`
Legge lo stream NMEA dal receiver Master e estrae coordinate dal messaggio GGA.

**Algoritmo**:
```python
1. Apri socket TCP verso ip_address:port
2. Leggi stream NMEA in buffer
3. Per ogni riga ricevuta:
   - Se contiene "$" e "GGA":
     - Parsifica con parse_gga()
     - Se coordinate valide:
       - Imposta coordinate
       - Chiudi socket
       - Ritorna True
4. Se timeout scade o stream termina:
   - Ritorna False
```

**Formato NMEA GGA**:
```
$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47
       └─time  └─lat────┘ └─lon─────┘ Q sats      └─alt─┘
```

---

### 4. Rover (`models/rover.py`)

**Responsabilità**: Receiver Rover che acquisisce posizione RTK tramite RTKRCV.

#### Metodi Principali

##### `process_with_rtkrcv(master, rtklib_path, timeout=300)`

Elabora il Rover eseguendo RTKRCV con correzioni differenziali dal Master.

**Flusso Completo**:

1. **Validazione**
   - Verifica che Master abbia coordinate valide

2. **Generazione Configurazione**
   - Chiama `generate_rtkrcv_config()` con parametri Master/Rover
   - File creato: `/tmp/rtkrcv_{serial}.conf`

3. **Preparazione Ambiente**
   - Crea directory `/tmp/rt/` per file RTKRCV
   - Definisce percorsi file output:
     - Solution: `/tmp/solution_{serial}.pos`
     - STDOUT: `/tmp/rtkrcv_stdout_{serial}.log`
     - STDERR: `/tmp/rtkrcv_stderr_{serial}.log`
     - Trace: `/tmp/rt/rtkrcv_*.trace` (dinamico)

4. **Avvio RTKRCV**
   ```python
   subprocess.Popen([
       rtklib_path, '-nc', '-t', '2', '-o', config_file
   ], cwd='/tmp/rt/', start_new_session=True)
   ```

   Opzioni:
   - `-nc`: No-console mode (avvio automatico)
   - `-t 2`: Debug level 2
   - `-o`: File di configurazione

5. **Monitoraggio Real-Time**
   ```python
   while time.time() - start_time < timeout:
       # Trova trace file dinamicamente
       trace_file = _find_latest_trace_file()

       # Legge ultime 3 righe
       current_lines = _read_last_n_lines(trace_file, 3)

       # Aggiorna display con ANSI overlay
       if current_lines != last_lines:
           # Cancella righe precedenti
           print("\033[A\033[K" * lines_printed)
           # Stampa nuove righe
           print("\n".join(current_lines))

       # Controlla file soluzione
       if solution_file.exists():
           coords = read_solution_file(solution_file)
           if coords and coords['quality'] == 1:  # Fix RTK
               self.set_coordinates(**coords)
               return True
   ```

6. **Terminazione Processo**
   - SIGTERM (graceful shutdown)
   - Se non risponde in 5s → SIGKILL

7. **Cleanup**
   - Rimuove file config e solution
   - **Se successo**: rimuove tutti i log
   - **Se errore**: preserva log per debugging

##### `_find_latest_trace_file(directory, pattern)`
Trova il file trace più recente nella directory che corrisponde al pattern `rtkrcv_*.trace`.

##### `_read_last_n_lines(file_path, n=2)`
Legge le ultime N righe non vuote di un file.

##### `_stop_rtkrcv(process)`
Ferma il processo RTKRCV in modo pulito (SIGTERM → SIGKILL).

##### `_print_log_files(stdout_file, stderr_file, trace_file)`
Stampa il contenuto dei file di log per debugging.

##### `_analyze_trace_file(trace_file)`
Analizza il file trace RTKRCV e mostra statistiche errori:
- Conta errori per tipo
- Identifica pattern problematici (parity errors, warnings)
- Suggerisce soluzioni per errori comuni

---

### 5. Utility: Parser NMEA (`utils/nmea_parser.py`)

##### `parse_gga(gga_sentence)`

Parsifica una stringa NMEA GGA e estrae coordinate geografiche.

**Formato Input**:
```
$GPGGA,time,lat,N/S,lon,E/W,quality,sats,hdop,alt,M,...
```

**Algoritmo**:

1. **Validazione Quality**: Verifica che `quality > 0`
2. **Parsing Latitudine**:
   ```python
   lat_raw = 4807.038  # DDMM.MMMM
   lat_deg = 48        # Gradi
   lat_min = 7.038     # Minuti
   lat = 48 + 7.038/60 = 48.1173°
   ```
3. **Parsing Longitudine**: Stesso algoritmo con formato `DDDMM.MMMM`
4. **Altitudine**: Estrazione diretta in metri

**Output**:
```python
{
    'lat': 48.1173,
    'lon': 11.5167,
    'alt': 545.4
}
```

---

### 6. Utility: Lettore Soluzione (`utils/solution_reader.py`)

##### `read_solution_file(solution_file)`

Legge il file di soluzione RTKLIB e estrae coordinate con fix RTK.

**Formato File RTKLIB (.pos)**:
```
% GPST         latitude(deg) longitude(deg) height(m) Q ns sdn sde sdu ...
2025/01/04 15:30:52.000 46.037124 13.253457 148.235 1 12 0.012 0.015 0.025 ...
                                                     │  └─ n.satelliti
                                                     └─ Quality (1=Fix)
```

**Quality Codes**:
- `1` = Fix RTK (precisione cm)
- `2` = Float RTK (precisione dm)
- `5` = Single (precisione m)

**Algoritmo**:
```python
# Legge dal fondo verso l'alto (ultima soluzione = migliore)
for line in reversed(lines):
    if quality == 1:  # Solo Fix RTK
        return {'lat': lat, 'lon': lon, 'alt': alt}
```

---

### 7. Utility: Validatore Configurazione (`utils/validator.py`)

##### `validate_config(config_path)`

Valida la struttura e i campi obbligatori del file YAML.

### 8. Utility: KML Writer (`utils/kml_writer.py`)

##### `write(receivers, output_path)`

Genera file KML con placemark per ogni receiver, includendo dettagli su tipo, master e stato soluzione.

### 10. Utility: Gestore Processi RTK (`utils/rtk_process.py`)

##### `RTKProcess(config_file, rtklib_path, output_dir)`

Gestisce l'esecuzione del processo binario `rtkrcv`, inclusi avvio, stop e monitoraggio file.

### 11. Utility: Verifica Stream (`utils/stream_verifier.py`)

##### `StreamVerifier.detect_protocol(ip, port)`

Verifica se una porta TCP è aperta e cerca di identificare il protocollo (UBX, NMEA, RTCM, ecc.) analizzando i byte ricevuti.

### 12. Utility: Generatore Config RTKRCV (`utils/rtklib_config.py`)

##### `generate_rtkrcv_config(rover_serial, rover_ip, rover_port, master_ip, master_port, master_lat, master_lon, master_alt)`

Genera un file di configurazione ottimizzato per RTKRCV.

**Parametri Template**:

| Sezione | Parametro | Valore | Descrizione |
|---------|-----------|--------|-------------|
| **Positioning** | `pos1-posmode` | `kinematic` | Modalità cinematica |
| | `pos1-frequency` | `l1+l2` | Dual-frequency |
| | `pos1-elmask` | `15°` | Elevazione minima |
| | `pos1-navsys` | `5` (GPS+GLO) | Sistemi GNSS |
| | `pos1-exclsats` | `C50,G46,...` | Satelliti esclusi |
| **Ambiguity** | `pos2-armode` | `continuous` | AR continuo |
| | `pos2-arthres` | `2.0` | Threshold ratio |
| | `pos2-minfixsats` | `4` | Satelliti minimi fix |
| | `pos2-maxage` | `30s` | Max età correzioni |
| **Input** | `inpstr1-type` | `tcpcli` | Stream Rover (TCP client) |
| | `inpstr2-type` | `tcpcli` | Stream Master (TCP client) |
| **Output** | `outstr1-type` | `file` | File soluzione |
| | `out-solformat` | `llh` | Formato lat/lon/height |
| **Log** | `log-level1` | `2` | Debug level |
| | `logstr1-type` | `file` | File trace |

**File Generato**: `/tmp/rtkrcv_{serial}.conf`

---

## Struttura dei File

```
rtkrcv_multi_session_handler/
│
├── main.py                    # Entry point del programma
├── stations.yaml              # Configurazione receiver GNSS
├── verify_streams.py          # Script standalone per verifica stream
├── requirements.txt           # Dipendenze Python
│
├── output/                    # Directory output KML
│   └── ...
│
├── tmp/                       # Directory file temporanei
│   └── ...
│
├── manager/
│   ├── __init__.py
│   └── rtk_manager.py         # Orchestratore principale (129 righe)
│
├── models/
│   ├── __init__.py
│   ├── receiver.py            # Classe base receiver (31 righe)
│   ├── master.py              # Receiver Master (45 righe)
│   ├── rover.py               # Receiver Rover (343 righe)
│   └── coordinates.py         # Dataclass coordinate
│
├── utils/
│   ├── __init__.py
│   ├── validator.py           # Validatore configurazione
│   ├── kml_writer.py          # Generatore output KML
│   ├── stream_verifier.py     # Analyzer protocolli stream
│   ├── rtk_process.py         # Wrapper subprocess rtkrcv
│   ├── nmea_parser.py         # Parser messaggi NMEA GGA (40 righe)
│   ├── solution_reader.py     # Lettore file soluzione RTKLIB (35 righe)
│   └── rtklib_config.py       # Generatore config RTKRCV (259 righe)
│
├── lib/
│   └── rtkrcv                 # Binario RTKLIB (compilato)
│
└── rtklib/                    # Git submodule RTKLIB Explorer
    └── ...
```

**Totale LOC Python**: ~899 linee (esclusi venv e rtklib)

---

## File Temporanei e Log

### Directory di Lavoro

- **RTKRCV Working Dir**: `/tmp/rt/`
- **File Temporanei**: `/tmp/`

### File Generati Durante l'Esecuzione

| File | Percorso | Descrizione | Cleanup |
|------|---------|-------------|---------|
| **Config RTKRCV** | `/tmp/rtkrcv_{serial}.conf` | Configurazione RTKRCV generata | Sempre rimosso |
| **Solution File** | `/tmp/solution_{serial}.pos` | File soluzione RTKLIB (coordinate) | Sempre rimosso |
| **STDOUT Log** | `/tmp/rtkrcv_stdout_{serial}.log` | Output standard RTKRCV | Rimosso se successo |
| **STDERR Log** | `/tmp/rtkrcv_stderr_{serial}.log` | Errori RTKRCV | Rimosso se successo |
| **Trace File** | `/tmp/rt/rtkrcv_*.trace` | Log dettagliato RTKRCV (debug level 2) | Rimosso se successo |
| **KML Output** | `output/output_*.kml` | File risultati finale | Persistente |

### Preservazione Log in Caso di Errore

Se l'elaborazione di un Rover fallisce, i file di log vengono **preservati** per debugging:

```
Log preservati per debug:
  STDOUT: /tmp/rtkrcv_stdout_2409-002.log
  STDERR: /tmp/rtkrcv_stderr_2409-002.log
  TRACE: /tmp/rt/rtkrcv_20250104_153045.trace
```

---

## Gestione degli Errori

### Categorie di Errori

#### 1. Errori di Configurazione

**Problema**: File `stations.yaml` non trovato o malformato

**Gestione**:
```python
if not self.yaml_path.exists():
    raise FileNotFoundError(f"File non trovato: {self.yaml_path}")
```

**Soluzione**: Verificare percorso e sintassi YAML

---

#### 2. Errori di Connessione Master

**Problema**: Impossibile connettersi al Master via TCP

**Sintomi**:
```
Acquisizione posizione Master da stream NMEA...
Errore lettura NMEA da Master: [Errno 111] Connection refused
Impossibile acquisire posizione Master
Impossibile proseguire senza posizione Master
```

**Cause Comuni**:
- Receiver Master offline
- IP/porta errati
- Firewall blocca connessione
- Stream NMEA non abilitato sul receiver

**Soluzione**:
1. Verificare connettività: `ping <master_ip>`
2. Testare porta TCP: `telnet <master_ip> <port>`
3. Verificare configurazione receiver (NMEA output enabled)

---

#### 3. Errori Stream NMEA

**Problema**: Stream NMEA non contiene messaggi GGA validi

**Sintomi**:
```
Acquisizione posizione Master da stream NMEA...
Impossibile acquisire posizione Master
```

**Cause**:
- Receiver invia solo altri tipi di messaggi NMEA
- Quality field = 0 (no fix GPS)
- Formato messaggio corrotto

**Debug**:
```python
# Aggiungi debug print in master.py:
for line in lines[:-1]:
    print(f"DEBUG: Ricevuto: {line}")
    if line.startswith('$') and 'GGA' in line:
        ...
```

---

#### 4. Errori Avvio RTKRCV

**Problema**: RTKRCV non si avvia o termina immediatamente

**Sintomi**:
```
Avvio RTKRCV per Rover 2409-002...
RTKRCV avviato in background (PID: 12345)
RTKRCV terminato inaspettatamente
```

**Cause**:
- Binario RTKRCV non trovato o non eseguibile
- File configurazione malformato
- Porte receiver già in uso

**Debug**: Controllare log STDERR
```bash
cat /tmp/rtkrcv_stderr_2409-002.log
```

**Soluzioni**:
1. Verificare binario: `ls -lh ./lib/rtkrcv && file ./lib/rtkrcv`
2. Testare manualmente: `./lib/rtkrcv -t 2 -o /tmp/test.conf`
3. Controllare permessi: `chmod +x ./lib/rtkrcv`

---

#### 5. Errori di Comunicazione Receiver

**Problema**: RTKRCV non riceve dati dai receiver

**Sintomi (Trace File)**:
```
ubx input error: parity error
ubx input error: parity error
ubx input error: parity error
```

**Analisi Automatica**: Il sistema analizza il trace e mostra:
```
⚠️  Rilevati 1250 errori di parità!
   Questo indica che il formato dello stream potrebbe essere errato.
   Verifica che i receiver trasmettano nel formato configurato (ubx).
```

**Cause**:
- Formato stream non corretto (es. NMEA invece di UBX)
- Baud rate errato
- Receiver offline

**Soluzioni**:
1. Verificare formato output receiver (deve essere UBX per Rover)
2. Controllare configurazione stream in `rtklib_config.py`:
   ```python
   inpstr1-format     =ubx
   ```
3. Testare connessione: `telnet <rover_ip> <port>`

---

#### 6. Timeout Elaborazione RTK

**Problema**: RTKRCV non raggiunge fix RTK entro il timeout (300s)

**Sintomi**:
```
Attendo inizializzazione RTKRCV...
[Monitoraggio per 300s]
Impossibile posizionare Rover 2409-002
```

**Cause**:
- Scarsa visibilità satelliti
- Interferenze RF
- Geometria satelliti sfavorevole (alto GDOP)
- Distanza Master-Rover eccessiva
- Correzioni differenziali non valide

**Analisi**:
Controllare trace file per:
- Numero satelliti disponibili: `ns=X` (minimo 4-5)
- Quality: `Q=2` (float) o `Q=5` (single) invece di `Q=1` (fix)
- Messaggi di warning

**Soluzioni**:
1. Aumentare timeout in `rover.py:16`:
   ```python
   def process_with_rtkrcv(self, master, rtklib_path, timeout: int = 600)
   ```
2. Ridurre elevazione minima (15° → 10°) in `rtklib_config.py`
3. Verificare distanza Master-Rover (max 10-20 km per L1+L2)
4. Attendere migliore visibilità satelliti

---

#### 7. Errori Half-Cycle Slips

**Problema**: Satelliti specifici causano ambiguity resolution instabile

**Sintomi**:
- Fix RTK intermittente (Q=1 ↔ Q=2)
- Salti di posizione inaspettati

**Soluzione**: Il sistema esclude automaticamente satelliti problematici:
```python
pos1-exclsats = C50,G46,S90,S145,S150
pos1-posopt6 = off  # Disabilita half-cycle detection
```

Se persistono problemi, aggiungere altri satelliti alla lista di esclusione.

---

## Troubleshooting

### Checklist Diagnostica

#### 1. Verificare Connettività

```bash
# Ping receiver
ping 10.158.0.190

# Test porta TCP
telnet 10.158.0.190 2222

# Se ricevi caratteri (anche illeggibili), la connessione funziona
```

#### 2. Verificare Stream NMEA/UBX

```bash
# Cattura stream NMEA (Master)
nc 10.158.0.190 2222 | head -n 20

# Cerca messaggi GGA
nc 10.158.0.190 2222 | grep GGA
```

Stream UBX (Rover) non è leggibile in ASCII (formato binario).

#### 3. Test Manuale RTKRCV

```bash
# Genera configurazione
python -c "from utils.rtklib_config import generate_rtkrcv_config; \
           generate_rtkrcv_config('TEST', '10.158.0.163', 2222, \
                                  '10.158.0.190', 2222, \
                                  46.037347, 13.253102, 149.258)"

# Avvia RTKRCV manualmente
cd /tmp/rt
/path/to/lib/rtkrcv -t 2 -o /tmp/rtkrcv_TEST.conf

# Monitora output
tail -f /tmp/rt/rtkrcv_*.trace
tail -f /tmp/solution_TEST.pos
```

#### 4. Analizzare Log Dettagliati

```bash
# Cerca errori specifici
grep -i error /tmp/rtkrcv_stderr_*.log
grep -i warning /tmp/rt/rtkrcv_*.trace

# Conta errori di parità
grep "parity error" /tmp/rt/rtkrcv_*.trace | wc -l

# Estrai statistiche satelliti
grep '$GNGGA' /tmp/rt/rtkrcv_*.trace | tail -n 20
```

#### 5. Validare Configurazione YAML

```python
import yaml

with open('stations.yaml') as f:
    data = yaml.safe_load(f)
    print(yaml.dump(data, default_flow_style=False))
```

---

### Problemi Comuni e Soluzioni

| Problema | Causa | Soluzione |
|----------|-------|-----------|
| "Connection refused" | Receiver offline o IP errato | Verificare ping e configurazione rete |
| "Impossibile acquisire posizione Master" | NMEA stream non valido | Verificare output NMEA e quality field |
| "parity error" ripetuti | Formato stream errato | Cambiare formato in config RTKRCV |
| Timeout 300s scaduto | Fix RTK non raggiunto | Aumentare timeout, verificare satelliti |
| Fix intermittente (Q=1↔Q=2) | Half-cycle slips | Aggiungere satelliti a exclsats |
| "File trace non trovato" | RTKRCV non scrive trace | Verificare permessi directory /tmp/rt |
| Posizione errata (offset metri) | Coordinate Master errate | Riacquisire posizione Master |

---

### Debug Avanzato

#### Abilitare Logging Verbose

Modificare `rover.py:72` per aumentare debug level:
```python
[str(rtklib_path_abs), '-nc', '-t', '5', '-o', str(config_file_abs)]
                                    # ↑ Debug level 5 (molto verboso)
```

#### Modificare Parametri RTKRCV

Editare template in `utils/rtklib_config.py`:

**Aumentare visibilità satelliti**:
```python
pos1-elmask = 10  # Ridurre da 15° a 10°
```

**Rilassare threshold AR**:
```python
pos2-arthres = 1.5  # Ridurre da 2.0 a 1.5 (meno stringente)
```

**Abilitare Galileo/BeiDou** (se supportati):
```python
pos1-navsys = 47  # 1:GPS + 2:SBAS + 4:GLO + 8:GAL + 32:BDS = 47
```

---

## Limitazioni Note

### Architetturali

1. **Elaborazione Sequenziale**: I Rover vengono processati uno alla volta, non in parallelo
   - **Impatto**: Tempo totale = Somma tempi individuali
   - **Miglioramento**: Implementare elaborazione concorrente con `multiprocessing`

2. **Singolo Master**: Supportato un solo receiver Master per sessione
   - **Limitazione**: Impossibile gestire reti RTK multi-base
   - **Workaround**: Eseguire sessioni separate per ogni base

3. **Timeout Fissi**: Timeout hardcoded nel codice (30s Master, 300s Rover)
   - **Limitazione**: Non configurabili via YAML
   - **Miglioramento**: Aggiungere parametri timeout in configurazione

4. **No Retry Logic**: Se acquisizione fallisce, non viene ritentata automaticamente
   - **Impatto**: Necessario riavvio manuale del programma
   - **Miglioramento**: Implementare retry con backoff esponenziale

### Operative

5. **Dipendenza da Fix RTK (Q=1)**: Accetta solo soluzioni con fix RTK completo
   - **Limitazione**: Ignora float (Q=2) anche se precisione accettabile
   - **Workaround**: Modificare `solution_reader.py:20` per accettare `quality == 2`

6. **GPS + GLONASS Only**: Galileo e BeiDou disabilitati per evitare problemi specifici
   - **Impatto**: Ridotta disponibilità satelliti in ambienti ostili
   - **Miglioramento**: Test approfonditi con Galileo per rienable

7. **Nessun Controllo Qualità Coordinate**: Non valida coordinate acquisite (outlier detection)
   - **Rischio**: Coordinate errate possono essere salvate in YAML
   - **Miglioramento**: Implementare validazione geometrica (es. distanza max da posizione precedente)

### Testing

8. **Assenza Test Automatizzati**: Nessun test unitario o di integrazione
   - **Impatto**: Regressioni non rilevate automaticamente
   - **Miglioramento**: Implementare suite pytest

9. **Documentazione Limitata**: Docstring minimali nel codice
   - **Impatto**: Difficoltà per nuovi sviluppatori
   - **Miglioramento**: Aggiungere docstring complete in formato Google/NumPy style

---

## Estensioni Future

### Funzionalità Proposte

1. **Elaborazione Parallela Rover**
   - Utilizzare `multiprocessing.Pool` per processare N Rover contemporaneamente
   - Riduzione tempo totale da O(N) a O(1)

2. **Interfaccia Web/GUI**
   - Dashboard real-time con mappa posizioni
   - Configurazione receiver via interfaccia grafica
   - Visualizzazione trace RTKRCV live

3. **Persistenza Database**
   - Storico posizioni in SQLite/PostgreSQL
   - Query temporali (es. posizione Rover X al tempo T)
   - Export dati in formati GIS (Shapefile, GeoJSON)

4. **Quality Control**
   - Validazione geometrica coordinate
   - Calcolo precision/accuracy metrics (CEP, RMS)
   - Outlier detection automatico

5. **Configurazione Avanzata**
   - Timeout configurabili in YAML
   - Parametri RTKRCV personalizzabili per receiver
   - Profili di configurazione (urban/open-sky/forest)

---

## Riferimenti

### RTKLIB

- **Repository Ufficiale**: https://github.com/tomojitakasu/RTKLIB
- **Manuale RTKLIB**: http://www.rtklib.com/prog/manual_2.4.2.pdf
- **RTKLIB Explorer**: Fork con miglioramenti UI

### Standard GNSS

- **NMEA 0183**: Standard per messaggi di navigazione
  - Spec GGA: https://docs.novatel.com/OEM7/Content/Logs/GPGGA.htm
- **UBX Protocol**: Protocollo proprietario u-blox
  - Spec: https://www.u-blox.com/sites/default/files/products/documents/u-blox8-M8_ReceiverDescrProtSpec_UBX-13003221.pdf
- **RTCM 3.x**: Standard correzioni differenziali RTK

### RTK Positioning

- **Principi RTK**: https://www.fig.net/resources/proceedings/fig_proceedings/cairo/papers/ts_21/ts21_06_rizos.pdf
- **Ambiguity Resolution**: Teunissen, P.J.G. (1995). "The least-squares ambiguity decorrelation adjustment"

---

## Contatti e Supporto

Per domande, bug report o contributi:

1. **Issues GitHub**: Aprire issue sul repository del progetto
2. **Pull Request**: Contributi via PR sono benvenuti
3. **Documentazione**: Riferirsi a questo documento per dettagli implementativi
