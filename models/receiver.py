from typing import Optional, Dict
from .coordinates import Coordinates

class Ricevitore:
    """Classe base per ricevitori GNSS"""
    def __init__(self, serial_number: str, ip_address: str, port: int, role: str):
        self.serial_number = serial_number
        self.ip_address = ip_address
        self.port = port
        self.role = role
        self.coords: Optional[Coordinates] = None
        self.running = False

    def set_coordinates(self, lat: float, lon: float, alt: float) -> None:
        """Imposta le coordinate del ricevitore"""
        self.coords = Coordinates(lat, lon, alt)

    def get_coordinates(self) -> Optional[Dict[str, float]]:
        if self.coords is None:
            return None
        return self.coords.to_dict()

    def has_coordinates(self) -> bool:
        """Verifica se le coordinate sono state impostate"""
        return self.coords is not None

    def __str__(self) -> str:
        base = f"Serial: {self.serial_number}, IP: {self.ip_address}, Port: {self.port}, Role: {self.role}"
        coords = str(self.coords) if self.coords else "Coordinates: Not set"
        return f"{base} | {coords}"
