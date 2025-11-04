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
        
        # Crea directory temporanea per i file RTKRCV
        rtkrcv_tmp_dir = Path(tempfile.gettempdir()) / "rt"
        rtkrcv_tmp_dir.mkdir(exist_ok=True, parents=True)

        # Definisci file soluzione e file temporanei
        solution_file = Path(tempfile.gettempdir()) / f"solution_{self.serial_number}.pos"
        stdout_file = Path(tempfile.gettempdir()) / f"rtkrcv_stdout_{self.serial_number}.log"
        stderr_file = Path(tempfile.gettempdir()) / f"rtkrcv_stderr_{self.serial_number}.log"
        trace_file = rtkrcv_tmp_dir / f"rtkrcv_{self.serial_number}.trace"
        print(f"File soluzione atteso: {solution_file}")
        print(f"Directory di lavoro RTKRCV: {rtkrcv_tmp_dir}")

        process = None
        stdout_fd = None
        stderr_fd = None
        try:
            # Avvia RTKRCV con opzione -nc (start automatically without console)
            # e -t 2 per debug level 2
            # Converti percorsi in assoluti per funzionare con cwd
            rtklib_path_abs = rtklib_path if rtklib_path.is_absolute() else Path.cwd() / rtklib_path
            config_file_abs = config_file if config_file.is_absolute() else Path.cwd() / config_file

            print(f"Avvio RTKRCV per Rover {self.serial_number}...")
            print(f"Comando: {rtklib_path_abs} -nc -t 2 -o {config_file_abs}")

            # Apri i file per redirection
            stdout_fd = open(stdout_file, 'w', buffering=1)  # Line buffering
            stderr_fd = open(stderr_file, 'w', buffering=1)  # Line buffering

            process = subprocess.Popen(
                [str(rtklib_path_abs), '-nc', '-t', '2', '-o', str(config_file_abs)],
                stdin=subprocess.DEVNULL,
                stdout=stdout_fd,
                stderr=stderr_fd,
                cwd=str(rtkrcv_tmp_dir),  # Esegue RTKRCV in /tmp/rt/
                start_new_session=True,  # Detach dal terminale
                close_fds=False  # NON chiudere i file descriptor
            )

            print(f"RTKRCV avviato in background (PID: {process.pid})")
            print(f"Log output: {stdout_file}")

            # Attendi avvio processo
            time.sleep(2)

            # Monitora il file di soluzione
            start_time = time.time()
            fixed = False

            while time.time() - start_time < timeout:
                # Flush dei file per assicurarsi che l'output venga scritto
                stdout_fd.flush()
                stderr_fd.flush()

                if solution_file.exists():
                    coords = read_solution_file(solution_file)
                    if coords:
                        self.set_coordinates(**coords)
                        fixed = True
                        print(f"Rover {self.serial_number} posizionato: Lat={coords['lat']}, Lon={coords['lon']}, Alt={coords['alt']}")
                        break

                # Verifica se il processo è ancora attivo
                if process.poll() is not None:
                    print(f"RTKRCV terminato inaspettatamente")
                    break

                time.sleep(1)

            # Ferma RTKRCV se ancora attivo
            self._stop_rtkrcv(process)

            # Chiudi i file descriptor DOPO aver fermato il processo
            stdout_fd.close()
            stderr_fd.close()

            # Stampa i log prima del cleanup
            if not fixed:
                print(f"\n=== Log RTKRCV per Rover {self.serial_number} ===")
                self._print_log_files(stdout_file, stderr_file, trace_file)

            # Cleanup - preserva i log in caso di errore
            config_file.unlink(missing_ok=True)
            solution_file.unlink(missing_ok=True)
            if fixed:
                # Rimuovi i log solo se il processo ha avuto successo
                stdout_file.unlink(missing_ok=True)
                stderr_file.unlink(missing_ok=True)
                trace_file.unlink(missing_ok=True)
            else:
                # Preserva i log in caso di errore
                print(f"Log preservati per debug:")
                print(f"  STDOUT: {stdout_file}")
                print(f"  STDERR: {stderr_file}")
                print(f"  TRACE: {trace_file}")

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
            for tmp_file in [stdout_file, stderr_file, trace_file, config_file, solution_file]:
                try:
                    tmp_file.unlink(missing_ok=True)
                except:
                    pass

            return False

    def _print_log_files(self, stdout_file: Path, stderr_file: Path, trace_file: Path = None):
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

            if trace_file and trace_file.exists():
                # Analizza il file trace e mostra statistiche errori
                self._analyze_trace_file(trace_file)
            elif trace_file:
                print(f"\nTRACE: (file non trovato)")
        except Exception as e:
            print(f"Errore nella lettura dei log: {e}")

    def _analyze_trace_file(self, trace_file: Path):
        """Analizza il file trace e mostra statistiche degli errori"""
        try:
            with open(trace_file, 'r') as f:
                lines = f.readlines()

            if not lines:
                print(f"\nTRACE: (vuoto)")
                return

            print(f"\n--- ANALISI TRACE ({trace_file}) ---")
            print(f"Righe totali: {len(lines)}")

            # Conta gli errori
            error_types = {}
            for line in lines:
                line = line.strip()
                if 'error' in line.lower() or 'warning' in line.lower():
                    # Estrai il tipo di errore
                    parts = line.split(':')
                    if len(parts) >= 2:
                        error_type = parts[0].strip() + ': ' + parts[1].strip().split(',')[0]
                        error_types[error_type] = error_types.get(error_type, 0) + 1

            if error_types:
                print(f"\nErrori/Warning trovati:")
                for error_type, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True)[:10]:
                    print(f"  {error_type}: {count} occorrenze")

                # Se ci sono molti errori di parità, suggerisci una soluzione
                if any('parity error' in err for err in error_types):
                    total_parity_errors = sum(count for err, count in error_types.items() if 'parity error' in err)
                    print(f"\n⚠️  Rilevati {total_parity_errors} errori di parità!")
                    print(f"   Questo indica che il formato dello stream potrebbe essere errato.")
                    print(f"   Verifica che i receiver trasmettano nel formato configurato (ubx).")
            else:
                print("Nessun errore trovato nel trace")
                # Mostra le ultime 20 righe per debug
                print("\nUltime 20 righe del trace:")
                for line in lines[-20:]:
                    print(f"  {line.rstrip()}")
        except Exception as e:
            print(f"Errore nell'analisi del trace: {e}")

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
