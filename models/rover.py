import subprocess
from pathlib import Path
from typing import Optional
from .receiver import Ricevitore
from utils.rtklib_config import generate_rtkrcv_config
from utils.rtk_process import RTKProcess

class Rover(Ricevitore):
    """Rover che riceve coordinate da RTKRCV"""
    def __init__(self, serial_number: str, ip_address: str, port: int):
        super().__init__(serial_number, ip_address, port, 'rover')

    def process_with_rtkrcv(self, master, rtklib_path: Path, timeout: int = 300) -> bool:
        """Avvia RTKRCV per ottenere posizione con correzioni differenziali"""
        if not master.has_coordinates():
            print(f"Master non ha coordinate impostate")
            return False

        # Directory temporanea locale al progetto per facilitare debug
        output_dir = Path("tmp")
        output_dir.mkdir(exist_ok=True)

        # Genera file configurazione RTKRCV
        config_file = generate_rtkrcv_config(
            rover_serial=self.serial_number,
            rover_ip=self.ip_address,
            rover_port=self.port,
            master_ip=master.ip_address,
            master_port=master.port,
            master_lat=master.coords.lat,
            master_lon=master.coords.lon,
            master_alt=master.coords.alt,
            output_dir=output_dir
        )
        
        # Verifica creazione file
        if not config_file.exists():
            print(f"ERRORE: File di configurazione non creato: {config_file}")
            return False
        
        print(f"File di configurazione creato: {config_file}")
        
        # Usa la nuova classe RTKProcess con output_dir locale
        rtk_process = RTKProcess(config_file, rtklib_path, output_dir=output_dir)
        
        if not rtk_process.start():
            return False
            
        print(f"\nAttendo soluzione FIX (timeout: {timeout}s)...")
        result = rtk_process.wait_for_fix(timeout)
        
        success = False
        if result:
            quality = result.get('quality', 0)
            status_str = "FIX" if quality == 1 else "FLOAT" if quality == 2 else "UNKNOWN"
            
            # Extract coordinates
            coords = {k: v for k, v in result.items() if k in ['lat', 'lon', 'alt']}
            self.set_coordinates(**coords)
            
            # Se Float, aggiunge nota (se possibile, la classe Receiver potrebbe non avere campo note, controllo)
            # Controllo base: Receiver ha coords che è un oggetto o dizionario?
            # Receiver.coords è probabile una namedtuple o oggetto semplice?
            # Controlliamo models/receiver.py se necessario, ma per ora teniamo semplice:
            msg = f"Rover {self.serial_number} posizionato ({status_str}): Lat={coords['lat']}, Lon={coords['lon']}, Alt={coords['alt']}"
            if quality != 1:
                msg += " (⚠️ Status non optimal)"
            print(msg)
            
            success = True
        else:
            print(f"Nessuna soluzione valida trovata nel tempo limite.")
            
        # Stop e cleanup
        # Se fallisce, tiene i log (keep_logs_on_success=False -> pulisce se successo, True se voglio debug)
        # La logica originale preservava i log in caso di errore
        rtk_process.stop(keep_logs_on_success=not success)
            
        return success
