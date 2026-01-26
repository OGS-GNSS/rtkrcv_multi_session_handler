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
        self.sol_status: Optional[str] = None
        self.linked_master_id: Optional[str] = None

    def set_coordinates(self, lat: float, lon: float, alt: float, status: str = None, master_id: str = None) -> None:
        """Imposta le coordinate del ricevitore"""
        self.coords = Coordinates(lat, lon, alt)
        if status:
            self.sol_status = status
        if master_id:
            self.linked_master_id = master_id

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
