from typing import Optional, Dict

def parse_gga(gga_sentence: str) -> Optional[Dict[str, float]]:
    """
    Parsifica una stringa NMEA GGA
    Formato: $GPGGA,time,lat,N/S,lon,E/W,quality,sats,hdop,alt,M,...
    """
    try:
        parts = gga_sentence.split(',')
        if len(parts) < 10:
            return None

        # Verifica quality (deve essere > 0)
        if int(parts[6]) == 0:
            return None

        # Latitudine: DDMM.MMMM -> DD.DDDDDD
        lat_raw = float(parts[2])
        lat_deg = int(lat_raw / 100)
        lat_min = lat_raw - (lat_deg * 100)
        lat = lat_deg + (lat_min / 60)
        if parts[3] == 'S':
            lat = -lat

        # Longitudine: DDDMM.MMMM -> DDD.DDDDDD
        lon_raw = float(parts[4])
        lon_deg = int(lon_raw / 100)
        lon_min = lon_raw - (lon_deg * 100)
        lon = lon_deg + (lon_min / 60)
        if parts[5] == 'W':
            lon = -lon

        # Altitudine
        alt = float(parts[9])

        return {'lat': lat, 'lon': lon, 'alt': alt}

    except (ValueError, IndexError):
        return None
