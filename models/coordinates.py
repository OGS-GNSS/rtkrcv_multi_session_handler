from dataclasses import dataclass

@dataclass
class Coordinates:
    lat: float
    lon: float
    alt: float

    def __str__(self) -> str:
        return f"Lat: {self.lat:.4f}, Lon: {self.lon:.4f}, Alt: {self.alt:.1f}"
    
    def to_dict(self) -> dict:
        return {'lat': self.lat, 'lon': self.lon, 'alt': self.alt}
