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
        
        # Definisci file soluzione e file temporanei
        solution_file = Path(tempfile.gettempdir()) / f"solution_{self.serial_number}.pos"
        stdout_file = Path(tempfile.gettempdir()) / f"rtkrcv_stdout_{self.serial_number}.log"
        stderr_file = Path(tempfile.gettempdir()) / f"rtkrcv_stderr_{self.serial_number}.log"
        print(f"File soluzione atteso: {solution_file}")

        process = None
        stdout_fd = None
        stderr_fd = None
        try:
            # Avvia RTKRCV con opzione -nc (start automatically without console)
            print(f"Avvio RTKRCV per Rover {self.serial_number}...")
            print(f"Comando: {rtklib_path} -nc -o {config_file}")

            # Apri i file per redirection
            stdout_fd = open(stdout_file, 'w')
            stderr_fd = open(stderr_file, 'w')

            process = subprocess.Popen(
                [str(rtklib_path), '-nc', '-o', str(config_file)],
                stdin=subprocess.DEVNULL,
                stdout=stdout_fd,
                stderr=stderr_fd,
                start_new_session=True,  # Detach dal terminale
                close_fds=True
            )

            # Chiudi i file descriptor nel processo padre
            stdout_fd.close()
            stderr_fd.close()

            print(f"RTKRCV avviato in background (PID: {process.pid})")
            print(f"Log output: {stdout_file}")

            # Attendi avvio processo
            time.sleep(2)

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
                    print(f"RTKRCV terminato inaspettatamente")
                    # Leggi i file di log invece di communicate()
                    self._print_log_files(stdout_file, stderr_file)
                    break

                time.sleep(1)

            # Ferma RTKRCV
            self._stop_rtkrcv(process)

            # Stampa i log prima del cleanup
            if not fixed:
                print(f"\n=== Log RTKRCV per Rover {self.serial_number} ===")
                self._print_log_files(stdout_file, stderr_file)

            # Cleanup - preserva i log in caso di errore
            config_file.unlink(missing_ok=True)
            solution_file.unlink(missing_ok=True)
            if fixed:
                # Rimuovi i log solo se il processo ha avuto successo
                stdout_file.unlink(missing_ok=True)
                stderr_file.unlink(missing_ok=True)
            else:
                # Preserva i log in caso di errore
                print(f"Log preservati per debug:")
                print(f"  STDOUT: {stdout_file}")
                print(f"  STDERR: {stderr_file}")

            return fixed

        except Exception as e:
            print(f"Errore durante elaborazione RTKRCV: {e}")
            traceback.print_exc()

            # Chiudi file descriptor se ancora aperti
            for fd in [stdout_fd, stderr_fd]:
                try:
                    if fd and not fd.closed:
                        fd.close()
                except:
                    pass

            # Termina processo se ancora attivo
            if process and process.poll() is None:
                process.kill()

            # Cleanup file temporanei
            for tmp_file in [stdout_file, stderr_file, config_file, solution_file]:
                try:
                    tmp_file.unlink(missing_ok=True)
                except:
                    pass

            return False

    def _print_log_files(self, stdout_file: Path, stderr_file: Path):
        """Legge e stampa il contenuto dei file di log"""
        try:
            if stdout_file.exists():
                with open(stdout_file, 'r') as f:
                    stdout_content = f.read()
                    if stdout_content.strip():
                        print(f"\n--- STDOUT ---")
                        print(stdout_content)
                    else:
                        print(f"\nSTDOUT: (vuoto)")
            else:
                print(f"\nSTDOUT: (file non trovato)")

            if stderr_file.exists():
                with open(stderr_file, 'r') as f:
                    stderr_content = f.read()
                    if stderr_content.strip():
                        print(f"\n--- STDERR ---")
                        print(stderr_content)
                    else:
                        print(f"\nSTDERR: (vuoto)")
            else:
                print(f"\nSTDERR: (file non trovato)")
        except Exception as e:
            print(f"Errore nella lettura dei log: {e}")

    def _stop_rtkrcv(self, process):
        """Ferma RTKRCV in modo pulito"""
        if process.poll() is not None:
            # Processo già terminato
            return

        try:
            # Prova prima con SIGTERM
            process.terminate()
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            # Se non risponde, forza kill
            print(f"RTKRCV non risponde, forzando terminazione...")
            process.kill()
            process.wait()
