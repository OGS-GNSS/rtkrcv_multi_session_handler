import subprocess
from pathlib import Path
from typing import Optional
from .receiver import Ricevitore
from utils.rtklib_config import generate_rtkrcv_config
from utils.rtk_process import RTKProcess

class Rover(Ricevitore):
    """Rover che riceve coordinate da RTKRCV"""
    """Rover che riceve coordinate da RTKRCV"""
    def __init__(self, serial_number: str, ip_address: str, port: int, timeout: int = 150):
        super().__init__(serial_number, ip_address, port, 'rover')
        self.timeout = timeout

    def process_with_rtkrcv(self, master, rtklib_path: Path) -> bool:
        """
        Avvia RTKRCV per ottenere posizione con correzioni differenziali.
        
        TENSION: Reliability vs Latency
        Il sistema attende un FIX RTK (Q=1) fino al timeout, sacrificando la latenza per
        l'accuratezza. Se il timeout scade, si accetta un FLOAT (Q=2) come fallback,
        bilanciando la necessità di avere un dato con la sua qualità.
        """
        if not master.has_coordinates():
            print(f"Master non ha coordinate impostate", flush=True)
            return False

        output_dir = Path("tmp")
        output_dir.mkdir(exist_ok=True)

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
        
        if not config_file.exists():
            print(f"ERRORE: File di configurazione non creato: {config_file}", flush=True)
            return False
            
        print(f"File di configurazione creato: {config_file}", flush=True)
        
        rtk_process = RTKProcess(config_file, rtklib_path, output_dir=output_dir)
        
        if not rtk_process.start():
            return False
            
        print(f"\nAttendo soluzione FIX (timeout: {self.timeout}s)...", flush=True)
        result = rtk_process.wait_for_fix(self.timeout)
        
        success = False
        if result:
            self._apply_solution(result, master.serial_number)
            success = True
        else:
            print(f"Nessuna soluzione valida trovata nel tempo limite.", flush=True)
            
        rtk_process.stop(keep_logs_on_success=not success)
        return success

    def _apply_solution(self, result: dict, master_id: str):
        """Applica la soluzione trovata al rover"""
        quality = result.get('quality', 0)
        status_str = "FIX" if quality == 1 else "FLOAT" if quality == 2 else "UNKNOWN"
        
        coords = {k: v for k, v in result.items() if k in ['lat', 'lon', 'alt']}
        self.set_coordinates(
            lat=coords['lat'], 
            lon=coords['lon'], 
            alt=coords['alt'],
            status=status_str,
            master_id=master_id
        )
        
        msg = f"Rover {self.serial_number} posizionato ({status_str}): Lat={coords['lat']}, Lon={coords['lon']}, Alt={coords['alt']}"
        if quality != 1:
            msg += " (⚠️ Status non optimal)"
        print(msg, flush=True)
