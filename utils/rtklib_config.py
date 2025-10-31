from pathlib import Path
import tempfile

def generate_rtkrcv_config(rover_serial: str, rover_ip: str, rover_port: int,
                          master_ip: str, master_port: int,
                          master_lat: float, master_lon: float, master_alt: float) -> Path:
    """Genera file di configurazione per RTKRCV"""
    
    tmp_file = Path(tempfile.gettempdir()) / f"rtkrcv_{rover_serial}.conf"
    solution_path = Path(tempfile.gettempdir()) / f"solution_{rover_serial}.pos"
    
    config_content = f"""# RTKRCV Configuration
console-passwd=admin
console-timetype=gpst

# Input streams
inpstr1-type=tcpcli
inpstr1-path={rover_ip}:{rover_port}
inpstr1-format=rtcm3

inpstr2-type=tcpcli
inpstr2-path={master_ip}:{master_port}
inpstr2-format=rtcm3

# Output stream
outstr1-type=file
outstr1-path={solution_path}
outstr1-format=llh

# Positioning mode
pos1-posmode=kinematic
pos1-frequency=l1+l2
pos1-soltype=forward
pos1-elmask=15
pos1-snrmask_r=off
pos1-dynamics=on

# Base station position (Master)
ant2-postype=llh
ant2-pos1={master_lat}
ant2-pos2={master_lon}
ant2-pos3={master_alt}
"""

    try:
        with open(tmp_file, 'w') as f:
            f.write(config_content)
        print(f"File di configurazione scritto: {tmp_file}")
        print(f"Dimensione file: {tmp_file.stat().st_size} bytes")
    except Exception as e:
        print(f"ERRORE nella scrittura del file di configurazione: {e}")
        raise

    return tmp_file
