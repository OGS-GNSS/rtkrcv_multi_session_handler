from pathlib import Path
from typing import List, Optional
import yaml
import datetime
from models.master import Master
from models.rover import Rover
from models.receiver import Ricevitore
from utils.kml_writer import KMLWriter
from utils.validator import Validator

class RTKManager:
    """Gestisce il processo completo di acquisizione coordinate RTK"""
    def __init__(self, yaml_path: Path, rtklib_path: Path):
        self.yaml_path = yaml_path
        self.rtklib_path = rtklib_path
        self.receivers: List[Ricevitore] = []
        self.master: Optional[Master] = None
        self.rovers: List[Rover] = []

    def load_receivers(self) -> None:
        """Carica ricevitori da file YAML"""
        # Validazione configurazione
        Validator.validate_config(self.yaml_path)

        with open(self.yaml_path, 'r') as f:
            data = yaml.safe_load(f)

        for item in data.get('receivers', {}).values():
            role = item.get('role')

            if role == 'master':
                self.master = Master(item['serial'], item['ip'], item['port'])
                # Carica coordinate se presenti nel YAML
                if 'coords' in item:
                    coords = item['coords']
                    self.master.set_coordinates(
                        lat=coords.get('lat'),
                        lon=coords.get('lon'),
                        alt=coords.get('alt')
                    )
                self.receivers.append(self.master)
            elif role == 'rover':
                timeout = item.get('timeout', 300)
                rover = Rover(item['serial'], item['ip'], item['port'], timeout)
                # Carica coordinate se presenti nel YAML
                if 'coords' in item:
                    coords = item['coords']
                    rover.set_coordinates(
                        lat=coords.get('lat'),
                        lon=coords.get('lon'),
                        alt=coords.get('alt')
                    )
                self.rovers.append(rover)
                self.receivers.append(rover)

    def acquire_master_position(self) -> bool:
        """Acquisisce posizione del Master da stream NMEA"""
        if not self.master:
            print("Nessun Master configurato", flush=True)
            return False

        print(f"Acquisizione posizione Master da stream NMEA...", flush=True)
        success = self.master.read_nmea_position()

        if success:
            print(f"Master posizionato: {self.master.coords}", flush=True)
            # Salvataggio solo alla fine
        else:
            print("Impossibile acquisire posizione Master", flush=True)

        return success

    def process_rovers(self) -> None:
        """
        Processa tutti i Rover per acquisire le loro posizioni.
        
        TENSION: Sequentiality vs Throughput
        I rover vengono processati sequenzialmente. Questo semplifica drasticamente il debugging
        e la gestione delle risorse (porte, CPU), ma aumenta il tempo totale di esecuzione
        linearmente con il numero di rover (O(N)). In un sistema di produzione con molti rover,
        questo sarebbe un collo di bottiglia critico.
        """
        if not self.master or not self.master.has_coordinates():
            print("Master non ha coordinate valide", flush=True)
            return

        for rover in self.rovers:
            print(f"\\nProcessing Rover {rover.serial_number}...", flush=True)
            success = rover.process_with_rtkrcv(self.master, self.rtklib_path)

            if success:
                print(f"Rover {rover.serial_number} posizionato: {rover.coords}", flush=True)
            else:
                print(f"Impossibile posizionare Rover {rover.serial_number}", flush=True)

    def save_results(self) -> None:
        """
        Salva risultati su file KML.
        
        TENSION: State vs Persistence
        Il sistema mantiene lo stato in memoria durante l'esecuzione e persiste i risultati
        solo alla fine. Questo evita scritture parziali e conflitti, ma comporta il rischio
        di perdere tutto il lavoro se il processo crasha prima della fine. L'alternativa
        sarebbe un database o un file di stato incrementale.
        """
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        output_filename = f"output_{timestamp}.kml"
        output_path = output_dir / output_filename

        KMLWriter.write(self.receivers, output_path)

    def run(self) -> None:
        """Esegue il workflow completo"""
        print("=== RTK Manager ===\n", flush=True)

        # Carica configurazione
        self.load_receivers()
        
        # Verifica connettività
        self._verify_all_receivers()
        
        # Filtra ricevitori attivi (già fatto in _verify_all_receivers, ma qui ricreiamo la lista completa)
        # Nota: _verify_all_receivers modifica self.rovers in-place rimuovendo quelli inattivi
        self.receivers = [self.master] + self.rovers if self.master else self.rovers
        
        if not self.rovers:
            print("Nessun Rover attivo disponibile. Esco.", flush=True)
            return

        print(f"Caricati {len(self.receivers)} ricevitori attivi", flush=True)

        # Acquisisce posizione Master
        if not self.master.has_coordinates():
            if not self.acquire_master_position():
                print("Impossibile proseguire senza posizione Master", flush=True)
                return
        else:
            print(f"Master già posizionato: {self.master.coords}", flush=True)

        # Processa Rover
        self.process_rovers()

        self.save_results()

        print("\n=== Processo completato ===", flush=True)
        for rcv in self.receivers:
            print(rcv, flush=True)

    def _verify_all_receivers(self):
        """Verifica connettività di tutti i ricevitori prima di iniziare"""
        print("Verifica connettività ricevitori...", flush=True)
        from utils.stream_verifier import StreamVerifier
        
        # Verify Master
        if self.master:
             print(f"Verifica Master {self.master.serial_number}...", end=' ', flush=True)
             proto = StreamVerifier.detect_protocol(self.master.ip_address, self.master.port)
             print(f"[{proto}]", flush=True)
             
             if proto in ['ERROR', 'TIMEOUT']:
                 print(f"⚠️  Master {self.master.serial_number} non raggiungibile ({proto}).", flush=True)
                 if not self.master.has_coordinates():
                     # Se master offline e senza coords, non possiamo procedere
                     # (In realtà potremmo se vogliamo solo processare rovers, ma servono i dati master!)
                     # TENSION: Robustness vs Flexibility
                     # Blocchiamo tutto se il master è critico.
                     return
                 else:
                     print("⚠️  Uso coordinate Master memorizzate.", flush=True)
             elif proto == 'SSH':
                    print(f"❌ Master su porta SSH (22)? Configurazione errata.", flush=True)
                    return
        
        # Verify Rovers
        active_rovers = []
        for rover in self.rovers:
            print(f"Verifica Rover {rover.serial_number}...", end=' ', flush=True)
            proto = StreamVerifier.detect_protocol(rover.ip_address, rover.port)
            print(f"[{proto}]", flush=True)
            
            if proto in ['ERROR', 'TIMEOUT']:
                 print(f"⚠️  Rover {rover.serial_number} non raggiungibile ({proto}). Skippo.", flush=True)
                 continue
            
            if proto == 'SSH':
                 print(f"❌ Rover {rover.serial_number} porta SSH rilevata. Skippo.", flush=True)
                 continue
                 
            if proto == 'NMEA':
                 print(f"⚠️  Attenzione: Rover {rover.serial_number} invia NMEA. RTKRCV richiede dati grezzi (UBX/RTCM).", flush=True)
            
            active_rovers.append(rover)
            
        self.rovers = active_rovers
