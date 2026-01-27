import subprocess
import time
import traceback
import tempfile
from pathlib import Path
from typing import Optional, List, Dict
from utils.solution_reader import read_solution_file

class RTKProcess:
    """Gestisce il ciclo di vita del processo RTKRCV"""
    
    def __init__(self, config_file: Path, rtklib_path: Path, output_dir: Optional[Path] = None):
        self.config_file = config_file
        self.rtklib_path = rtklib_path
        # Use temp dir if not provided, consistent with original logic
        self.output_dir = output_dir or Path(tempfile.gettempdir())
        
        # Paths management
        self.rtkrcv_tmp_dir = self.output_dir / "rt"
        self.rtkrcv_tmp_dir.mkdir(exist_ok=True, parents=True)
        
        # Derive filenames based on config filename logic or passed explicitly?
        # Original logic used serial number to name files. 
        # To avoid passing serial everywhere, let's assume unique config filenames or handle it internally.
        # Let's use the config stem as identifier
        identifier = config_file.stem.replace("rtkrcv_", "").replace(".conf", "")
        
        self.solution_file = self.output_dir / f"solution_{identifier}.pos"
        self.stdout_file = self.output_dir / f"rtkrcv_stdout_{identifier}.log"
        self.stderr_file = self.output_dir / f"rtkrcv_stderr_{identifier}.log"
        self.trace_file_pattern = "rtkrcv_*.trace" # RTKRCV dynamic naming
        
        self.process = None
        self.stdout_fd = None
        self.stderr_fd = None
        self.trace_file = None
        
        # State
        self.lines_printed = 0
        self.last_trace_lines = []

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
            
            print(f"RTKRCV avviato in background (PID: {self.process.pid})")
            print(f"File soluzione atteso: {self.solution_file}")
            print(f"Log output: {self.stdout_file}")
            print(f"Cercherò il file trace in: {self.rtkrcv_tmp_dir}/{self.trace_file_pattern}")
            
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
        
        Il filtro mediano riduce l'impatto di eventuali outliers nella prima acquisizione.
        """
        start_time = time.time()
        last_waiting_msg = 0
        best_solution = None
        fix_solutions = []  # Accumula soluzioni FIX per filtro mediano
        
        try:
            while time.time() - start_time < timeout:
                self.stdout_fd.flush()
                self.stderr_fd.flush()
                
                elapsed = time.time() - start_time
                remaining = timeout - elapsed
                
                # Prepare status line
                status_line = None
                
                # Check solution
                if self.solution_file.exists():
                    if not hasattr(self, '_sol_file_seen'):
                        print(f"File soluzione creato: {self.solution_file} (analizzo content...)", end='\n')
                        self._sol_file_seen = True
                        
                    sol = read_solution_file(self.solution_file)
                    if sol:
                        quality = sol.get('quality', 0)
                        q_str = "FIX" if quality == 1 else "FLOAT" if quality == 2 else f"Q={quality}"
                        
                        # Mostra progresso raccolta campioni FIX
                        fix_progress = f" [{len(fix_solutions)}/{median_samples}]" if fix_solutions else ""
                        status_line = f"Soluzione corrente: {sol['lat']:.8f}, {sol['lon']:.8f}, {sol['alt']:.3f} ({q_str}{fix_progress}) - Time: {remaining:.0f}s"

                        # Se abbiamo FIX (Q=1), accumula per filtro mediano
                        if quality == 1:
                            # Evita duplicati (stesso timestamp/coordinate identiche)
                            if not fix_solutions or self._is_new_solution(sol, fix_solutions[-1]):
                                fix_solutions.append(sol)
                                print(f"  ✓ Campione FIX #{len(fix_solutions)} raccolto")
                            
                            # Se abbiamo abbastanza campioni, calcola mediana
                            if len(fix_solutions) >= median_samples:
                                if self.lines_printed > 0:
                                    print("\033[A\033[K" * self.lines_printed, end="")
                                median_sol = self._compute_median_solution(fix_solutions)
                                print(f"  📊 Soluzione mediana calcolata da {len(fix_solutions)} campioni")
                                return median_sol
                        
                        # Se abbiamo FLOAT (Q=2), salviamolo come fallback
                        if quality == 2:
                            best_solution = sol

                # Check trace file with status
                self._update_trace_output(elapsed, status_line)

                # Check process status
                if self.process.poll() is not None:
                    print(f"\nRTKRCV terminato inaspettatamente")
                    return best_solution # Ritorna quel che abbiamo
                    
                # Waiting message
                if self.trace_file is None and elapsed > 5 and elapsed - last_waiting_msg > 10:
                    print(f"Attendo file trace... ({int(elapsed)}s)")
                    last_waiting_msg = elapsed
                    
                time.sleep(1)
            
            # Timeout scaduto
            if best_solution:
                print(f"\nTimeout scaduto. Accetto soluzione FLOAT.")
                return best_solution
                
            return None
            
        except KeyboardInterrupt:
            print("\nInterrotto dall'utente")
            return best_solution
        finally:
            self._cleanup_display()

    def _update_trace_output(self, elapsed: float, extra_status_line: Optional[str] = None):
        """Aggiorna il display con le ultime righe del file trace e status opzionale"""
        if self.trace_file is None:
            self.trace_file = self._find_latest_trace_file()
            if self.trace_file:
                 print(f"\n✓ File trace trovato: {self.trace_file.name}")
                 print(f"--- Monitoraggio RTKRCV (ultime 3 righe aggiornate in tempo reale) ---")

        if self.trace_file and self.trace_file.exists():
            current_lines = self._read_last_n_lines(self.trace_file, 3)
            
            # Combine trace lines and status line
            display_lines = list(current_lines)
            if extra_status_line:
                display_lines.append("") # Spacer
                display_lines.append(extra_status_line)

            # Update if changed
            if display_lines != self.last_trace_lines:
                # Clear previous lines
                if self.lines_printed > 0:
                     for _ in range(self.lines_printed):
                        print(f"\033[A\033[K", end='')
                
                # Print new lines
                for line in display_lines:
                    print(f"{line}")
                
                self.lines_printed = len(display_lines)
                self.last_trace_lines = display_lines

    def _cleanup_display(self):
        """Pulisce l'output del trace fine monitoraggio"""
        if self.lines_printed > 0:
            print()

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
             # Normal cleanup
             self.config_file.unlink(missing_ok=True)
             self.solution_file.unlink(missing_ok=True)
             self.stdout_file.unlink(missing_ok=True)
             self.stderr_file.unlink(missing_ok=True)
             if self.trace_file:
                 self.trace_file.unlink(missing_ok=True)
        else:
            # Print logs for debug before leaving
            self._print_log_summary()

    def _print_log_summary(self):
        """Stampa riepilogo log in caso di errori"""
        try:
             print(f"\n=== Log RTKRCV ===")
             self._cat_file(self.stdout_file, "STDOUT")
             self._cat_file(self.stderr_file, "STDERR")
             
             if self.trace_file and self.trace_file.exists():
                 self._analyze_trace_file(self.trace_file)
             else:
                 print("\nTRACE: (non trovato)")
                 
             print(f"\nLog file salvati in {self.output_dir}")
        except Exception as e:
            print(f"Errore stampa log: {e}")

    def _cat_file(self, path: Path, label: str):
        if path.exists():
            content = path.read_text().strip()
            print(f"\n--- {label} ---")
            print(content if content else "(vuoto)")
        else:
             print(f"\n{label}: (file non trovato)")

    def _find_latest_trace_file(self) -> Optional[Path]:
        try:
            files = list(self.rtkrcv_tmp_dir.glob(self.trace_file_pattern))
            if not files: return None
            return max(files, key=lambda p: p.stat().st_mtime)
        except:
            return None

    def _read_last_n_lines(self, path: Path, n: int) -> list:
        try:
            with open(path, 'r') as f:
                lines = f.readlines()
                non_empty = [l.rstrip() for l in lines if l.strip()]
                return non_empty[-n:] if len(non_empty) >= n else non_empty
        except:
            return []

    def _analyze_trace_file(self, trace_file: Path):
        try:
            with open(trace_file, 'r') as f:
                lines = f.readlines()
            
            print(f"\n--- ANALISI TRACE ({trace_file.name}) ---")
            print(f"Righe totali: {len(lines)}")
            
            error_types = {}
            for line in lines:
                if 'error' in line.lower() or 'warning' in line.lower():
                    # Simple extraction
                    parts = line.strip().split(':')
                    if len(parts) >= 2:
                        etype = parts[0].strip() + ': ' + parts[1].strip().split(',')[0]
                        error_types[etype] = error_types.get(etype, 0) + 1
            
            if error_types:
                print(f"\nErrori/Warning:")
                for etype, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True)[:10]:
                    print(f"  {etype}: {count}")
                
                if any('parity error' in k for k in error_types):
                     print(f"\n⚠️  Errori di parità rilevati! Verifica baudrate/formato.")
            else:
                print("Nessun errore evidente.")
                print("Ultime 20 righe:")
                for line in lines[-20:]:
                    print(f"  {line.rstrip()}")
        except Exception as e:
            print(f"Errore analisi trace: {e}")

    def _is_new_solution(self, sol: Dict, prev_sol: Dict) -> bool:
        """Verifica se la soluzione è diversa dalla precedente (evita duplicati)"""
        # Considera nuova se le coordinate differiscono oltre una soglia minima
        threshold = 1e-9  # ~0.1mm, evita duplicati esatti
        return (
            abs(sol['lat'] - prev_sol['lat']) > threshold or
            abs(sol['lon'] - prev_sol['lon']) > threshold or
            abs(sol['alt'] - prev_sol['alt']) > 0.001  # 1mm per altitudine
        )

    def _compute_median_solution(self, solutions: List[Dict]) -> Dict:
        """
        Calcola la soluzione con coordinate mediane.
        Per ogni coordinata (lat, lon, alt), prende il valore mediano.
        Restituisce una copia della soluzione con coordinate mediane.
        """
        import statistics
        
        lats = [s['lat'] for s in solutions]
        lons = [s['lon'] for s in solutions]
        alts = [s['alt'] for s in solutions]
        
        median_sol = solutions[0].copy()  # Mantieni quality e altri campi
        median_sol['lat'] = statistics.median(lats)
        median_sol['lon'] = statistics.median(lons)
        median_sol['alt'] = statistics.median(alts)
        
        return median_sol
