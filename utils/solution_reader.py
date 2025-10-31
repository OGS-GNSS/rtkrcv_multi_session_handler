from pathlib import Path
from typing import Optional, Dict

def read_solution_file(solution_file: Path) -> Optional[Dict[str, float]]:
    """Legge il file di soluzione RTKLIB e estrae le coordinate con fix"""
    try:
        with open(solution_file, 'r') as f:
            lines = f.readlines()
            
        # Cerca l'ultima linea con fix valido (Q=1)
        for line in reversed(lines):
            if line.startswith('%') or line.strip() == '':
                continue
                
            parts = line.split()
            if len(parts) >= 5:
                # Formato: GPST lat lon height Q ns sdn sde sdu sdne sdeu sdun age ratio
                # Posizione 4 è Q (quality): 1=Fix, 2=Float, 5=Single
                try:
                    quality = int(parts[4])
                    if quality == 1:  # Solo fix RTK
                        return {
                            'lat': float(parts[1]),
                            'lon': float(parts[2]),
                            'alt': float(parts[3])
                        }
                except (ValueError, IndexError):
                    continue
                    
        return None
        
    except Exception as e:
        print(f"Errore lettura file soluzione: {e}")
        return None
