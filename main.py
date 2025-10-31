from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import dataclass
import yaml
import socket
import subprocess
import tempfile
import re
import time
import traceback


@dataclass
class Coordinates:
    lat: float
    lon: float
    alt: float

    def __str__(self) -> str:
        return f"Lat: {self.lat:.4f}, Lon: {self.lon:.4f}, Alt: {self.alt:.1f}"


class Ricevitore:
    """Classe base per ricevitori GNSS"""
    def __init__(self, serial_number: str, ip_address: str, port: int, role: str):
        self.serial_number = serial_number
        self.ip_address = ip_address
        self.port = port
        self.role = role
        self.coords: Optional[Coordinates] = None
        self.running = False

    def set_coordinates(self, lat: float, lon: float, alt: float) -> None:
        """Imposta le coordinate del ricevitore"""
        self.coords = Coordinates(lat, lon, alt)

    def get_coordinates(self) -> Optional[Dict[str, float]]:
        if self.coords is None:
            return None
        return {'lat': self.coords.lat, 'lon': self.coords.lon, 'alt': self.coords.alt}

    def has_coordinates(self) -> bool:
        """Verifica se le coordinate sono state impostate"""
        return self.coords is not None

    def __str__(self) -> str:
        base = f"Serial: {self.serial_number}, IP: {self.ip_address}, Port: {self.port}, Role: {self.role}"
        coords = str(self.coords) if self.coords else "Coordinates: Not set"
        return f"{base} | {coords}"


class Master(Ricevitore):
    """Master che riceve coordinate da stream NMEA"""
    def __init__(self, serial_number: str, ip_address: str, port: int):
        super().__init__(serial_number, ip_address, port, 'master')

    def read_nmea_position(self, timeout: int = 30) -> bool:
        """
        Legge lo stream NMEA dal Master e estrae la posizione da una stringa GGA

        Args:
            timeout: Secondi massimi di attesa per una posizione valida

        Returns:
            True se la posizione è stata acquisita con successo
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((self.ip_address, self.port))

            buffer = ""
            while True:
                data = sock.recv(1024).decode('ascii', errors='ignore')
                if not data:
                    break

                buffer += data
                lines = buffer.split('\n')
                buffer = lines[-1]

                for line in lines[:-1]:
                    line = line.strip()
                    if line.startswith('$') and 'GGA' in line:
                        coords = self._parse_gga(line)
                        if coords:
                            self.set_coordinates(**coords)
                            sock.close()
                            return True

            sock.close()
            return False

        except Exception as e:
            print(f"Errore lettura NMEA da Master: {e}")
            return False

    def _parse_gga(self, gga_sentence: str) -> Optional[Dict[str, float]]:
        """
        Parsifica una stringa NMEA GGA
        Formato: $GPGGA,time,lat,N/S,lon,E/W,quality,sats,hdop,alt,M,...
        """
        try:
            parts = gga_sentence.split(',')
            if len(parts) < 10:
                return None

            # Verifica quality (deve essere > 0)
            if int(parts[6]) == 0:
                return None

            # Latitudine: DDMM.MMMM -> DD.DDDDDD
            lat_raw = float(parts[2])
            lat_deg = int(lat_raw / 100)
            lat_min = lat_raw - (lat_deg * 100)
            lat = lat_deg + (lat_min / 60)
            if parts[3] == 'S':
                lat = -lat

            # Longitudine: DDDMM.MMMM -> DDD.DDDDDD
            lon_raw = float(parts[4])
            lon_deg = int(lon_raw / 100)
            lon_min = lon_raw - (lon_deg * 100)
            lon = lon_deg + (lon_min / 60)
            if parts[5] == 'W':
                lon = -lon

            # Altitudine
            alt = float(parts[9])

            return {'lat': lat, 'lon': lon, 'alt': alt}

        except (ValueError, IndexError) as e:
            return None


class Rover(Ricevitore):
    """Rover che riceve coordinate da RTKRCV"""
    def __init__(self, serial_number: str, ip_address: str, port: int):
        super().__init__(serial_number, ip_address, port, 'rover')

    def process_with_rtkrcv(self, master: Master, rtklib_path: Path,
                           timeout: int = 300) -> bool:
        """
        Avvia RTKRCV per ottenere posizione con correzioni differenziali
        """
        if not master.has_coordinates():
            print(f"Master non ha coordinate impostate")
            return False

        # Genera file configurazione RTKRCV
        config_file = self._generate_rtkrcv_config(master)
        
        # DEBUG: Verifica che il file sia stato creato
        if not config_file.exists():
            print(f"ERRORE: File di configurazione non creato: {config_file}")
            return False
        else:
            print(f"File di configurazione creato: {config_file}")
        
        # Definisci il nome del file soluzione PRIMA di avviare RTKRCV
        solution_file = Path(tempfile.gettempdir()) / f"solution_{self.serial_number}.pos"
        print(f"File soluzione atteso: {solution_file}")

        process = None
        try:
            # Avvia RTKRCV in background con stdin per comandi
            print(f"Avvio RTKRCV per Rover {self.serial_number}...")
            print(f"Comando: {rtklib_path} -o {config_file}")
            
            process = subprocess.Popen(
                [str(rtklib_path), '-o', str(config_file)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )

            # Invia comando 'start' per avviare il processing
            process.stdin.write('start\n')
            process.stdin.flush()
            print("Comando 'start' inviato a RTKRCV")

            # Monitora il file di soluzione per il fix
            start_time = time.time()
            fixed = False

            while time.time() - start_time < timeout:
                if solution_file.exists():
                    print(f"File soluzione trovato: {solution_file}")
                    coords = self._read_solution_file(solution_file)
                    if coords:
                        self.set_coordinates(**coords)
                        fixed = True
                        break
                
                # Verifica se il processo è ancora attivo
                if process.poll() is not None:
                    stdout, stderr = process.communicate()
                    print(f"RTKRCV terminato inaspettatamente")
                    print(f"STDOUT: {stdout}")
                    print(f"STDERR: {stderr}")
                    break

                time.sleep(1)

            # Ferma RTKRCV con comando 'stop' e poi 'shutdown'
            try:
                process.stdin.write('stop\n')
                process.stdin.flush()
                time.sleep(0.5)
                process.stdin.write('shutdown\n')
                process.stdin.flush()
            except:
                pass

            # Attendi terminazione o forza kill
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

            # Cleanup
            config_file.unlink(missing_ok=True)
            solution_file.unlink(missing_ok=True)

            return fixed

        except Exception as e:
            print(f"Errore durante elaborazione RTKRCV: {e}")
            traceback.print_exc()
            if process and process.poll() is None:
                process.kill()
            return False

    def _generate_rtkrcv_config(self, master: Master) -> Path:
        """Genera file di configurazione per RTKRCV"""
        
        # Crea file temporaneo
        tmp_file = Path(tempfile.gettempdir()) / f"rtkrcv_{self.serial_number}.conf"
        
        # Definisci il path del file soluzione nel temp
        solution_path = Path(tempfile.gettempdir()) / f"solution_{self.serial_number}.pos"
        
        config_content = f"""# RTKRCV Configuration
console-passwd=admin
console-timetype=gpst

# Input streams
inpstr1-type=tcpcli
inpstr1-path={self.ip_address}:{self.port}
inpstr1-format=rtcm3

inpstr2-type=tcpcli
inpstr2-path={master.ip_address}:{master.port}
inpstr2-format=rtcm3

# Output stream
outstr1-type=file
outstr1-path={solution_path}
outstr1-format=llh

# Positioning mode
pos1-posmode=kinematic
pos1-frequency=l1+l2
pos1-soltype=forward
pos1-elmask=15
pos1-snrmask_r=off
pos1-dynamics=on

# Base station position (Master)
ant2-postype=llh
ant2-pos1={master.coords.lat}
ant2-pos2={master.coords.lon}
ant2-pos3={master.coords.alt}
"""

        try:
            with open(tmp_file, 'w') as f:
                f.write(config_content)
            print(f"File di configurazione scritto: {tmp_file}")
            print(f"Dimensione file: {tmp_file.stat().st_size} bytes")
        except Exception as e:
            print(f"ERRORE nella scrittura del file di configurazione: {e}")
            raise

        return tmp_file

    def _read_solution_file(self, solution_file: Path) -> Optional[Dict[str, float]]:
        """Legge il file di soluzione e estrae le coordinate con fix"""
        try:
            with open(solution_file, 'r') as f:
                lines = f.readlines()
                
            # Cerca l'ultima linea con fix valido (Q=1 o Q=2)
            for line in reversed(lines):
                if line.startswith('%') or line.strip() == '':
                    continue
                    
                parts = line.split()
                if len(parts) >= 5:
                    # Formato tipico: GPST lat lon height Q ns sdn sde sdu sdne sdeu sdun age ratio
                    # Posizione 4 è Q (quality): 1=Fix, 2=Float, 5=Single
                    try:
                        quality = int(parts[4])
                        if quality == 1:  # Solo fix RTK
                            return {
                                'lat': float(parts[1]),
                                'lon': float(parts[2]),
                                'alt': float(parts[3])
                            }
                    except (ValueError, IndexError):
                        continue
                        
            return None
            
        except Exception as e:
            print(f"Errore lettura file soluzione: {e}")
            return None


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


if __name__ == "__main__":
    manager = RTKManager(
        yaml_path=Path("./list.yaml"),
        rtklib_path=Path("./lib/rtkrcv")
    )

    manager.run()
