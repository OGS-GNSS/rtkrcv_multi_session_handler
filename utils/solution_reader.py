from pathlib import Path
from typing import Optional, Dict

def read_solution_file(solution_file: Path) -> Optional[Dict]:
    """Legge il file di soluzione RTKLIB e estrae le coordinate con fix/float"""
    try:
        with open(solution_file, 'r') as f:
            lines = f.readlines()
            
        # Cerca l'ultima linea valida
        for line in reversed(lines):
            if line.startswith('%') or line.strip() == '':
                continue
                
            parts = line.split()
            if len(parts) >= 6:
                # Formato: Date Time Lat Lon Height Q ns sdn sde sdu sdne sdeu sdun age ratio
                # parts[0]=Date, parts[1]=Time 
                # parts[2]=Lat, parts[3]=Lon, parts[4]=Height
                # parts[5]=Q (quality): 1=Fix, 2=Float
                try:
                    quality = int(parts[5])
                    if quality in [1, 2]:  # Fix (1) o Float (2)
                        return {
                            'lat': float(parts[2]),
                            'lon': float(parts[3]),
                            'alt': float(parts[4]),
                            'quality': quality
                        }
                except (ValueError, IndexError):
                    continue
                    
        return None
        
    except Exception as e:
        print(f"Errore lettura file soluzione: {e}")
        return None
