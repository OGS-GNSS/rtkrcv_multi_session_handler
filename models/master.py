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
        Legge lo stream NMEA dal Master e estrae la posizione da una stringa GGA
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
                        coords = parse_gga(line)
                        if coords:
                            self.set_coordinates(**coords)
                            sock.close()
                            return True

            sock.close()
            return False

        except Exception as e:
            print(f"Errore lettura NMEA da Master: {e}")
            return False
