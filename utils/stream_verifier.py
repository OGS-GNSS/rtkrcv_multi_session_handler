import socket
import time
import binascii

class StreamVerifier:
    @staticmethod
    def check_reachability(ip: str, port: int, timeout: int = 3) -> bool:
        """Verifica se l'host è raggiungibile sulla porta specificata"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(timeout)
                s.connect((ip, int(port)))
                return True
        except:
            return False

    @staticmethod
    def detect_protocol(ip: str, port: int, timeout: int = 5) -> str:
        """
        Tenta di rilevare il protocollo dello stream.
        Ritorna: 'UBX', 'RTCM3', 'NMEA', 'SSH', 'UNKNOWN', o 'ERROR'
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(timeout)
                s.connect((ip, int(port)))
                
                # Read a chunk
                data = s.recv(1024)
                if not data:
                    return "EMPTY"
                
                # Check signatures
                if data.startswith(b'\xb5\x62'):
                    return "UBX"
                elif data.startswith(b'\xd3'):
                    return "RTCM3"
                elif data.startswith(b'SSH-'):
                    return "SSH"
                
                # Check NMEA (ASCII $)
                # Some NMEA streams might have leading garbage or newlines
                # Scan first 64 bytes for '$GP' or '$GN'
                try:
                    text = data[:256].decode('ascii', errors='ignore')
                    if '$GP' in text or '$GN' in text or '$GL' in text or '$GA' in text:
                        return "NMEA"
                except:
                    pass
                
                return "UNKNOWN"
                
        except socket.timeout:
            return "TIMEOUT"
        except Exception:
            return "ERROR"
