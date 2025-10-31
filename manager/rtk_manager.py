from pathlib import Path
from typing import List, Optional
import yaml
from models.master import Master
from models.rover import Rover
from models.receiver import Ricevitore

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
        if not self.yaml_path.exists():
            raise FileNotFoundError(f"File non trovato: {self.yaml_path}")

        with open(self.yaml_path, 'r') as f:
            data = yaml.safe_load(f)

        for item in data.get('receivers', {}).values():
            role = item.get('role')

            if role == 'master':
                self.master = Master(item['serial'], item['ip'], item['port'])
                self.receivers.append(self.master)
            elif role == 'rover':
                rover = Rover(item['serial'], item['ip'], item['port'])
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
            self.save_config()
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
                self.save_config()
            else:
                print(f"Impossibile posizionare Rover {rover.serial_number}")

    def save_config(self) -> None:
        """Salva configurazione aggiornata con coordinate"""
        data = {'receivers': {}}

        for rcv in self.receivers:
            rcv_data = {
                'serial': rcv.serial_number,
                'ip': rcv.ip_address,
                'port': rcv.port,
                'role': rcv.role
            }

            if rcv.has_coordinates():
                rcv_data['coords'] = rcv.get_coordinates()

            data['receivers'][rcv.serial_number] = rcv_data

        with open(self.yaml_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False)

        print(f"Configurazione salvata in {self.yaml_path}")

    def run(self) -> None:
        """Esegue il workflow completo"""
        print("=== RTK Manager ===\n")

        # Carica configurazione
        self.load_receivers()
        print(f"Caricati {len(self.receivers)} ricevitori")

        # Acquisisce posizione Master
        if not self.master.has_coordinates():
            if not self.acquire_master_position():
                print("Impossibile proseguire senza posizione Master")
                return
        else:
            print(f"Master già posizionato: {self.master.coords}")

        # Processa Rover
        self.process_rovers()

        print("\n=== Processo completato ===")
        for rcv in self.receivers:
            print(rcv)
