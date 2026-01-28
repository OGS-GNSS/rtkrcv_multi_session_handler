import subprocess
import time
import tempfile
from pathlib import Path
from typing import Optional, List, Dict
from utils.solution_reader import read_solution_file

class RTKProcess:
    """Gestisce il ciclo di vita del processo RTKRCV"""
    
    def __init__(self, config_file: Path, rtklib_path: Path, output_dir: Optional[Path] = None):
        self.config_file = config_file
        self.rtklib_path = rtklib_path
        self.output_dir = output_dir or Path(tempfile.gettempdir())
        
        # Paths management
        self.rtkrcv_tmp_dir = self.output_dir / "rt"
        self.rtkrcv_tmp_dir.mkdir(exist_ok=True, parents=True)
        
        identifier = config_file.stem.replace("rtkrcv_", "").replace(".conf", "")
        
        self.solution_file = self.output_dir / f"solution_{identifier}.pos"
        self.stdout_file = self.output_dir / f"rtkrcv_stdout_{identifier}.log"
        self.stderr_file = self.output_dir / f"rtkrcv_stderr_{identifier}.log"
        
        self.process = None
        self.stdout_fd = None
        self.stderr_fd = None
        
        # State per output dinamico
        self.last_status_line = ""

    def start(self) -> bool:
        """Avvia il processo RTKRCV"""
        try:
            rtklib_path_abs = self.rtklib_path if self.rtklib_path.is_absolute() else Path.cwd() / self.rtklib_path
            config_file_abs = self.config_file if self.config_file.is_absolute() else Path.cwd() / self.config_file

            print(f"Comando: {rtklib_path_abs} -nc -t 2 -o {config_file_abs}")

            self.stdout_fd = open(self.stdout_file, 'w', buffering=1)
            self.stderr_fd = open(self.stderr_file, 'w', buffering=1)

            self.process = subprocess.Popen(
                [str(rtklib_path_abs), '-nc', '-t', '2', '-o', str(config_file_abs)],
                stdin=subprocess.DEVNULL,
                stdout=self.stdout_fd,
                stderr=self.stderr_fd,
                cwd=str(self.rtkrcv_tmp_dir),
                start_new_session=True,
                close_fds=False
            )
            
            print(f"RTKRCV avviato (PID: {self.process.pid})")
            print(f"File soluzione: {self.solution_file}")
            
            return True
        except Exception as e:
            print(f"Errore avvio RTKRCV: {e}")
            self.stop()
            return False

    def wait_for_fix(self, timeout: int = 300, median_samples: int = 3) -> Optional[Dict]:
        """
        Attende che venga trovata una soluzione.
        Raccoglie N soluzioni FIX (default 3) e restituisce quella con coordinate mediane.
        Se scade il timeout e c'è una soluzione FLOAT, restituisce quella.
        """
        start_time = time.time()
        best_solution = None
        fix_solutions = []
        
        try:
            while time.time() - start_time < timeout:
                self.stdout_fd.flush()
                self.stderr_fd.flush()
                
                elapsed = time.time() - start_time
                remaining = timeout - elapsed
                
                # Check solution file
                if self.solution_file.exists():
                    sol = read_solution_file(self.solution_file)
                    if sol:
                        quality = sol.get('quality', 0)
                        q_str = "FIX" if quality == 1 else "FLOAT" if quality == 2 else f"Q={quality}"
                        
                        fix_progress = f" [{len(fix_solutions)}/{median_samples}]" if fix_solutions else ""
                        status_line = f"Soluzione: {sol['lat']:.8f}, {sol['lon']:.8f}, {sol['alt']:.3f} ({q_str}{fix_progress}) - {remaining:.0f}s"
                        
                        # Aggiorna status su stessa riga
                        self._update_status(status_line)

                        # Se abbiamo FIX (Q=1), accumula per filtro mediano
                        if quality == 1:
                            if not fix_solutions or self._is_new_solution(sol, fix_solutions[-1]):
                                fix_solutions.append(sol)
                                print(f"\n  ✓ Campione FIX #{len(fix_solutions)} raccolto")
                            
                            if len(fix_solutions) >= median_samples:
                                print()  # Newline finale
                                median_sol = self._compute_median_solution(fix_solutions)
                                print(f"  📊 Soluzione mediana da {len(fix_solutions)} campioni")
                                return median_sol
                        
                        # FLOAT come fallback
                        if quality == 2:
                            best_solution = sol
                else:
                    self._update_status(f"Attendo soluzione... {remaining:.0f}s")

                # Check process status
                if self.process.poll() is not None:
                    print(f"\nRTKRCV terminato inaspettatamente")
                    return best_solution
                    
                time.sleep(1)
            
            # Timeout scaduto
            print()  # Newline finale
            if best_solution:
                print(f"Timeout scaduto. Accetto soluzione FLOAT.")
                return best_solution
                
            return None
            
        except KeyboardInterrupt:
            print("\nInterrotto dall'utente")
            return best_solution

    def _update_status(self, status_line: str):
        """Aggiorna lo status su una singola riga (sovrascrive)"""
        if status_line != self.last_status_line:
            # Use structured logging with newline so it's flushable by app.py
            print(f"[RTK_STATUS] {status_line}", flush=True)
            self.last_status_line = status_line

    def stop(self, keep_logs_on_success: bool = False):
        """Ferma il processo e pulisce le risorse"""
        # Stop process
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                 self.process.kill()
                 self.process.wait()
        
        # Close descriptors
        for fd in [self.stdout_fd, self.stderr_fd]:
            try:
                if fd and not fd.closed:
                    fd.close()
            except:
                pass
                
        # Handle logs
        if not keep_logs_on_success:
             self.config_file.unlink(missing_ok=True)
             self.solution_file.unlink(missing_ok=True)
             self.stdout_file.unlink(missing_ok=True)
             self.stderr_file.unlink(missing_ok=True)
        else:
            self._print_log_summary()

    def _print_log_summary(self):
        """Stampa riepilogo log in caso di errori"""
        try:
            print(f"\n=== Log RTKRCV ===")
            for path, label in [(self.stdout_file, "STDOUT"), (self.stderr_file, "STDERR")]:
                if path.exists():
                    content = path.read_text().strip()
                    print(f"\n--- {label} ---")
                    print(content if content else "(vuoto)")
            print(f"\nLog salvati in {self.output_dir}")
        except Exception as e:
            print(f"Errore stampa log: {e}")

    def _is_new_solution(self, sol: Dict, prev_sol: Dict) -> bool:
        """Verifica se la soluzione è diversa dalla precedente (evita duplicati)"""
        threshold = 1e-9
        return (
            abs(sol['lat'] - prev_sol['lat']) > threshold or
            abs(sol['lon'] - prev_sol['lon']) > threshold or
            abs(sol['alt'] - prev_sol['alt']) > 0.001
        )

    def _compute_median_solution(self, solutions: List[Dict]) -> Dict:
        """Calcola la soluzione con coordinate mediane."""
        import statistics
        
        median_sol = solutions[0].copy()
        median_sol['lat'] = statistics.median([s['lat'] for s in solutions])
        median_sol['lon'] = statistics.median([s['lon'] for s in solutions])
        median_sol['alt'] = statistics.median([s['alt'] for s in solutions])
        
        return median_sol
