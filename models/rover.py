import subprocess
import time
import traceback
import tempfile
from pathlib import Path
from typing import Optional
from .receiver import Ricevitore
from utils.rtklib_config import generate_rtkrcv_config
from utils.solution_reader import read_solution_file

class Rover(Ricevitore):
    """Rover che riceve coordinate da RTKRCV"""
    def __init__(self, serial_number: str, ip_address: str, port: int):
        super().__init__(serial_number, ip_address, port, 'rover')

    def process_with_rtkrcv(self, master, rtklib_path: Path, timeout: int = 300) -> bool:
        """Avvia RTKRCV per ottenere posizione con correzioni differenziali"""
        if not master.has_coordinates():
            print(f"Master non ha coordinate impostate")
            return False

        # Genera file configurazione RTKRCV
        config_file = generate_rtkrcv_config(
            rover_serial=self.serial_number,
            rover_ip=self.ip_address,
            rover_port=self.port,
            master_ip=master.ip_address,
            master_port=master.port,
            master_lat=master.coords.lat,
            master_lon=master.coords.lon,
            master_alt=master.coords.alt
        )
        
        # Verifica creazione file
        if not config_file.exists():
            print(f"ERRORE: File di configurazione non creato: {config_file}")
            return False
        
        print(f"File di configurazione creato: {config_file}")
        
        # Definisci file soluzione
        solution_file = Path(tempfile.gettempdir()) / f"solution_{self.serial_number}.pos"
        print(f"File soluzione atteso: {solution_file}")

        process = None
        try:
            # Avvia RTKRCV
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

            # Invia comando 'start'
            process.stdin.write('start\n')
            process.stdin.flush()
            print("Comando 'start' inviato a RTKRCV")

            # Monitora il file di soluzione
            start_time = time.time()
            fixed = False

            while time.time() - start_time < timeout:
                if solution_file.exists():
                    print(f"File soluzione trovato: {solution_file}")
                    coords = read_solution_file(solution_file)
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

            # Ferma RTKRCV
            self._stop_rtkrcv(process)

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

    def _stop_rtkrcv(self, process):
        """Ferma RTKRCV in modo pulito"""
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
