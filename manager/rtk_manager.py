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
            print("Nessun Master configurato")
            return False

        print(f"Acquisizione posizione Master da stream NMEA...")
        success = self.master.read_nmea_position()

        if success:
            print(f"Master posizionato: {self.master.coords}")
            # Salvataggio solo alla fine
        else:
            print("Impossibile acquisire posizione Master")

        return success

    def process_rovers(self) -> None:
        """Processa tutti i Rover per acquisire le loro posizioni"""
        if not self.master or not self.master.has_coordinates():
            print("Master non ha coordinate valide")
            return

        for rover in self.rovers:
            print(f"\nProcessing Rover {rover.serial_number}...")
            success = rover.process_with_rtkrcv(self.master, self.rtklib_path)

            if success:
                print(f"Rover {rover.serial_number} posizionato: {rover.coords}")
            else:
                print(f"Impossibile posizionare Rover {rover.serial_number}")

    def save_results(self) -> None:
        """Salva risultati su file KML"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        output_filename = f"output_{timestamp}.kml"
        output_path = output_dir / output_filename

        KMLWriter.write(self.receivers, output_path)

    def run(self) -> None:
        """Esegue il workflow completo"""
        print("=== RTK Manager ===\n")

        # Carica configurazione
        self.load_receivers()
        
        # --- VERIFICA ROBUSTEZZA ---
        print("Verifica connettività ricevitori...")
        from utils.stream_verifier import StreamVerifier
        
        # Verify Master
        if self.master:
             print(f"Verifica Master {self.master.serial_number}...", end=' ')
             proto = StreamVerifier.detect_protocol(self.master.ip_address, self.master.port)
             print(f"[{proto}]")
             
             if proto in ['ERROR', 'TIMEOUT']:
                 print(f"⚠️  Master {self.master.serial_number} non raggiungibile ({proto}).")
                 if not self.master.has_coordinates():
                     print("❌ Criticita: Master offline e senza coordinate. Impossibile procedere.")
                     return
                 else:
                     print("⚠️  Uso coordinate Master memorizzate.")
             elif proto == 'SSH':
                    print(f"❌ Master su porta SSH (22)? Configurazione errata.")
                    return
        
        # Verify Rovers
        active_rovers = []
        for rover in self.rovers:
            print(f"Verifica Rover {rover.serial_number}...", end=' ')
            proto = StreamVerifier.detect_protocol(rover.ip_address, rover.port)
            print(f"[{proto}]")
            
            if proto in ['ERROR', 'TIMEOUT']:
                 print(f"⚠️  Rover {rover.serial_number} non raggiungibile. Skippo.")
                 continue
            
            if proto == 'SSH':
                 print(f"❌ Rover {rover.serial_number} porta SSH rilevata. Skippo.")
                 continue
                 
            if proto == 'NMEA':
                 print(f"⚠️  Attenzione: Rover {rover.serial_number} invia NMEA. RTKRCV richiede dati grezzi (UBX/RTCM).")
            
            active_rovers.append(rover)
            
        self.rovers = active_rovers
        self.receivers = [self.master] + self.rovers if self.master else self.rovers
        
        if not self.rovers:
            print("Nessun Rover attivo disponibile. Esco.")
            return

        print(f"Caricati {len(self.receivers)} ricevitori attivi")

        # Acquisisce posizione Master
        if not self.master.has_coordinates():
            if not self.acquire_master_position():
                print("Impossibile proseguire senza posizione Master")
                return
        else:
            print(f"Master già posizionato: {self.master.coords}")

        # Processa Rover
        self.process_rovers()

        self.save_results()

        print("\n=== Processo completato ===")
        for rcv in self.receivers:
            print(rcv)
