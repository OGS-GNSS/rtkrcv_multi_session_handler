import socket
from typing import Optional, Dict
from .receiver import Ricevitore
from utils.nmea_parser import parse_gga

class Master(Ricevitore):
    """Master che riceve coordinate da stream NMEA"""
    def __init__(self, serial_number: str, ip_address: str, port: int):
        super().__init__(serial_number, ip_address, port, 'master')

    def read_nmea_position(self, timeout: int = 30) -> bool:
        """
        Legge la posizione NMEA dal socket.
        Raccoglie 10 campioni validi e calcola la mediana per maggiore precisione.
        """
        import socket
        import time
        import statistics
        from utils.nmea_parser import parse_gga

        start_time = time.time()
        samples = []
        
        print(f"Acquisizione posizione Master (target: 10 campioni)...")
        
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(10) # Socket timeout
                try:
                    s.connect((self.ip_address, self.port))
                except ConnectionRefusedError:
                    print(f"Errore lettura NMEA da Master: Connection refused")
                    return False
                except Exception as e:
                    print(f"Errore connessione Master: {e}")
                    return False

                buffer = ""
                while time.time() - start_time < timeout and len(samples) < 10:
                    try:
                        chunk = s.recv(1024).decode('ascii', errors='ignore')
                        if not chunk:
                            if not samples:
                                break
                            # Keep trying if we have partial samples? No, stream closed.
                            break
                            
                        buffer += chunk
                        while '\n' in buffer:
                            line, buffer = buffer.split('\n', 1)
                            line = line.strip()
                            
                            if line.startswith('$') and 'GGA' in line:
                                coords = parse_gga(line)
                                if coords:
                                    samples.append(coords)
                                    print(f"[MASTER_STATUS] Campione {len(samples)}/10: {coords['lat']:.6f}, {coords['lon']:.6f}, {coords['alt']:.2f}", flush=True)
                                    
                    except socket.timeout:
                        break
                    except Exception:
                        break
        
        except Exception as e:
            print(f"Errore inatteso Master: {e}")
            return False

        if not samples:
             print("\nNessun campione valido acquisito da Master.")
             return False
             
        # Calcolo mediana
        print(f"\nCalcolo mediana su {len(samples)} campioni...")
        
        lats = [s['lat'] for s in samples]
        lons = [s['lon'] for s in samples]
        alts = [s['alt'] for s in samples]
        
        med_lat = statistics.median(lats)
        med_lon = statistics.median(lons)
        med_alt = statistics.median(alts)
        
        self.set_coordinates(med_lat, med_lon, med_alt)
        return True

