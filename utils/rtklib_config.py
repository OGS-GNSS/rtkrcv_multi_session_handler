from pathlib import Path
import tempfile

def generate_rtkrcv_config(rover_serial: str, rover_ip: str, rover_port: int,
                          master_ip: str, master_port: int,
                          master_lat: float, master_lon: float, master_alt: float) -> Path:
    """Genera file di configurazione ottimizzato per RTKRCV con gestione errori UBX"""

    tmp_file = Path(tempfile.gettempdir()) / f"rtkrcv_{rover_serial}.conf"
    solution_path = Path(tempfile.gettempdir()) / f"solution_{rover_serial}.pos"
    # Trace file deve essere nella directory /tmp/rt/ dove RTKRCV viene eseguito
    rtkrcv_tmp_dir = Path(tempfile.gettempdir()) / "rt"
    trace_path = rtkrcv_tmp_dir / f"rtkrcv_{rover_serial}.trace"
    
    config_content = f"""# RTKRCV Configuration - Advanced UBX Error Handling
console-passwd=admin
console-timetype   =utc       # (0:gpst,1:utc,2:jst,3:tow)
console-soltype    =dms       # (0:dms,1:deg,2:xyz,3:enu,4:pyl)
console-solflag    =off       # (0:off,1:std+2:age/ratio/ns)
console-dev        =          # no console device needed

# OPTIONS 1 - POSITIONING
pos1-posmode       =kinematic # (0:single,1:dgps,2:kinematic,3:static,4:movingbase,5:fixed,6:ppp-kine,7:ppp-static)
pos1-frequency     =l1+l2     # (1:l1,2:l1+l2,3:l1+l2+l5,4:l1+l2+l5+l6,5:l1+l2+l5+l6+l7)
pos1-soltype       =forward   # (0:forward,1:backward,2:combined)
pos1-elmask        =15        # (deg) - Ridotto a 15 per avere più satelliti disponibili
pos1-snrmask_r     =on        # (0:off,1:on)
pos1-snrmask_b     =on        # (0:off,1:on)
pos1-snrmask_L1    =30,30,30,30,30,30,30,30,30  # SNR threshold per L1
pos1-snrmask_L2    =25,25,25,25,25,25,25,25,25  # SNR threshold per L2
pos1-snrmask_L5    =25,25,25,25,25,25,25,25,25  # SNR threshold per L5
pos1-dynamics      =on        # (0:off,1:on)
pos1-tidecorr      =off       # (0:off,1:on,2:otl)
pos1-ionoopt       =dual-freq # (0:off,1:brdc,2:sbas,3:dual-freq,4:est-stec...)
pos1-tropopt       =saas      # (0:off,1:saas,2:sbas,3:est-ztd,4:est-ztdgrad)
pos1-sateph        =brdc      # (0:brdc,1:precise,2:brdc+sbas,3:brdc+ssrapc,4:brdc+ssrcom)
pos1-posopt1       =off       # satellite PCV variation correction
pos1-posopt2       =off       # receiver PCV variation correction
pos1-posopt3       =off       # phase windup correction
pos1-posopt4       =off       # exclude measurements of eclipse satellite
pos1-posopt5       =off       # RAIM FDE (fault detection and exclusion)
pos1-posopt6       =off       # DISABILITA HALF-CYCLE DETECTION - IMPORTANTE!
# ESCLUSIONE SATELLITI PROBLEMATICI
# C50 = BeiDou PRN 50 (sys=32 prn=50)
# G46 = GPS PRN 46 che causa half-cycle slips
pos1-exclsats      =C50,G46,S90,S145,S150  # Esclusi tutti i satelliti problematici
# SISTEMI GNSS: Usa solo GPS+GLONASS (5 = 1+4), escludi Galileo e BeiDou
pos1-navsys        =5         # (1:gps+4:glo) SOLO GPS E GLONASS!

# OPTIONS 2 - AMBIGUITY RESOLUTION
pos2-armode        =continuous # (0:off,1:continuous,2:instantaneous,3:fix-and-hold)
pos2-gloarmode     =on        # (0:off,1:on,2:autocal)
pos2-arfilter      =on        # (0:off,1:on)
pos2-bdsarmode     =off       # (0:off,1:on) - DISABILITATO perché BeiDou è escluso
pos2-arlockcnt     =10        # Aumentato a 10 epoche per maggiore stabilità
pos2-arthres       =2.0       # Threshold ratio ridotto a 2.0
pos2-arthres1      =0.9       # Threshold per partial fix
pos2-arthres2      =0.25      # 
pos2-arthres3      =1E-5      # 
pos2-arthres4      =1E-2      # 
pos2-minfixsats    =4         # Satelliti minimi per fix
pos2-minholdsats   =5         # Satelliti minimi per mantenere fix
pos2-arelmask      =15        # (deg) elevation mask per AR
pos2-aroutcnt      =20        # Aumentato per gestire meglio outlier
pos2-arminfix      =10        # Epoche minime per fix
pos2-armaxiter     =1         # Iterazioni AR
pos2-elmaskhold    =15        # (deg) elevation mask per hold
pos2-slipthres     =0.05      # (m) Threshold per cycle slip detection
pos2-maxage        =30        # (s) Max age delle correzioni differenziali
pos2-syncsol       =off       # (0:off,1:on)
pos2-rejionno      =30        # (m) Reject threshold per residui ionosferici
pos2-rejgdop       =30        # Reject threshold per GDOP
pos2-niter         =1         # Numero iterazioni filtro
pos2-baselen       =0         # (m) Constraint baseline length (0=no constraint)
pos2-basesig       =0         # (m) Baseline length sigma

# OUTPUT CONFIGURATION
out-solformat      =llh       # (0:llh,1:xyz,2:enu,3:nmea)
out-outhead        =on        # (0:off,1:on)
out-outopt         =off       # (0:off,1:on)
out-timesys        =gpst      # (0:gpst,1:utc,2:jst)
out-timeform       =hms       # (0:tow,1:hms)
out-timendec       =3
out-degform        =deg       # (0:deg,1:dms)
out-fieldsep       =
out-height         =ellipsoidal # (0:ellipsoidal,1:geodetic)
out-geoid          =internal  # (0:internal,1:egm96,2:egm08_2.5,3:egm08_1,4:gsi2000)
out-solstatic      =all       # (0:all,1:single)
out-nmeaintv1      =1         # (s)
out-nmeaintv2      =1         # (s)
out-outstat        =residual  # (0:off,1:state,2:residual) - per debug
out-outsingle      =on        # Output anche single solutions

# STATISTICS - OTTIMIZZATI PER HALF-CYCLE SLIPS
stats-eratio1      =300       # Error ratio per L1
stats-eratio2      =300       # Error ratio per L2
stats-errphase     =0.003     # (m) Std dev errore di fase
stats-errphaseel   =0.003     # (m) Elevation-dependent phase error
stats-errphasebl   =0         # (m/10km) Baseline-length dependent error
stats-errdoppler   =1         # (Hz) Doppler error
stats-stdbias      =30        # (m) Carrier bias std dev
stats-stdiono      =0.03      # (m) Iono delay std dev
stats-stdtrop      =0.3       # (m) Trop delay std dev
stats-prnaccelh    =10        # (m/s^2) Horizontal acceleration - aumentato per dinamiche
stats-prnaccelv    =10        # (m/s^2) Vertical acceleration - aumentato per dinamiche
stats-prnbias      =0.0001    # (m) Process noise carrier bias
stats-prniono      =0.001     # (m) Process noise iono delay
stats-prntrop      =0.0001    # (m) Process noise trop delay
stats-clkstab      =5e-12     # (s/s) Clock stability

# ANTENNA CONFIGURATION - ROVER
ant1-postype       =single    # Rover antenna position type
ant1-pos1          =0         # (deg|m)
ant1-pos2          =0         # (deg|m)
ant1-pos3          =0         # (m|m)
ant1-anttype       =*         # Auto-detect antenna type
ant1-antdele       =0         # (m) Antenna delta E
ant1-antdeln       =0         # (m) Antenna delta N
ant1-antdelu       =0         # (m) Antenna delta U
ant1-maxaveep      =1         # Max averaging epoches for moving baseline

# ANTENNA CONFIGURATION - BASE/MASTER
ant2-postype       =llh       # (0:llh,1:xyz,2:single,3:posfile,4:rinexhead,5:rtcm)
ant2-pos1          ={master_lat}  # (deg|m) LAT
ant2-pos2          ={master_lon}  # (deg|m) LON  
ant2-pos3          ={master_alt}  # (m|m) H
ant2-anttype       =*         # Auto-detect antenna type
ant2-antdele       =0         # (m)
ant2-antdeln       =0         # (m)
ant2-antdelu       =0         # (m)
ant2-maxaveep      =1         # Max averaging epoches

# INPUT STREAMS CONFIGURATION
# Stream 1 - Rover
inpstr1-type       =tcpcli
inpstr1-path       ={rover_ip}:{rover_port}
inpstr1-format     =ubx
inpstr1-nmeareq    =off       # NMEA request to receiver
inpstr1-nmealat    =0         # NMEA position latitude
inpstr1-nmealon    =0         # NMEA position longitude

# Stream 2 - Base/Master
inpstr2-type       =tcpcli
inpstr2-path       ={master_ip}:{master_port}
inpstr2-format     =ubx
inpstr2-nmeareq    =off

# Stream 3 - Disabled
inpstr3-type       =off

# OUTPUT STREAMS
# Stream 1 - Solution file
outstr1-type       =file
outstr1-path       ={solution_path}
outstr1-format     =llh

# Stream 2 - Disabled  
outstr2-type       =off

# LOG STREAMS - All disabled
logstr1-type       =off
logstr2-type       =off
logstr3-type       =off

# MISCELLANEOUS
misc-svrcycle      =10        # (ms) Server cycle time
misc-timeout       =10000     # (ms) Timeout time
misc-reconnect     =10000     # (ms) Reconnect interval
misc-nmeacycle     =5000      # (ms) NMEA request cycle
misc-buffsize      =32768     # (bytes) Input buffer size
misc-navmsgsel     =rover     # (0:all,1:rover,2:base,3:corr) - CAMBIATO A ROVER ONLY
misc-proxyaddr     =          # HTTP/NTRIP proxy address
misc-fswapmargin   =30        # File swap margin

# FILE PATHS
file-satantfile    =          # Satellite antenna file
file-rcvantfile    =          # Receiver antenna file  
file-staposfile    =          # Station position file
file-geoidfile     =          # Geoid data file
file-dcbfile       =          # DCB data file
file-tempdir       =          # Temporary directory
file-geexefile     =          # Google Earth exe file
file-solstatfile   =          # Solution status file
file-tracefile     ={trace_path}  # Debug trace file

# MONITOR PORTS - All disabled
monitor-port1      =0         # Output monitor port 1 (0:off)
monitor-port2      =0         # Output monitor port 2 (0:off)
monitor-level1     =0         # Output level for monitor 1
monitor-level2     =0         # Output level for monitor 2
"""

    try:
        with open(tmp_file, 'w') as f:
            f.write(config_content)
        print(f"File di configurazione avanzato scritto: {tmp_file}")
        print(f"Dimensione file: {tmp_file.stat().st_size} bytes")
        print("\nMODIFICHE PRINCIPALI:")
        print("- Solo GPS e GLONASS abilitati (navsys=5)")
        print("- Galileo e BeiDou completamente disabilitati")
        print("- Half-cycle detection disabilitato (pos1-posopt6=off)")
        print("- GPS PRN 46 escluso per half-cycle slips")
        print("- Message selection: solo rover (misc-navmsgsel=rover)")
        print("- Dynamics aumentate per gestire movimenti rapidi")
    except Exception as e:
        print(f"ERRORE nella scrittura del file di configurazione: {e}")
        raise

    return tmp_file


def generate_minimal_config(rover_serial: str, rover_ip: str, rover_port: int,
                           master_ip: str, master_port: int,
                           master_lat: float, master_lon: float, master_alt: float) -> Path:
    """Genera configurazione MINIMALE solo GPS+GLONASS per testing"""
    
    tmp_file = Path(tempfile.gettempdir()) / f"rtkrcv_{rover_serial}_minimal.conf"
    solution_path = Path(tempfile.gettempdir()) / f"solution_{rover_serial}.pos"
    
    config_content = f"""# MINIMAL RTKRCV Config - GPS+GLONASS Only
pos1-posmode       =kinematic
pos1-frequency     =l1        # SOLO L1 per semplicità
pos1-elmask        =15
pos1-navsys        =5         # Solo GPS (1) + GLONASS (4)
pos1-exclsats      =          # Nessuna esclusione iniziale

pos2-armode        =fix-and-hold
pos2-arthres       =3.0
pos2-arlockcnt     =0
pos2-minfixsats    =4
pos2-minholdsats   =5

ant2-postype       =llh
ant2-pos1          ={master_lat}
ant2-pos2          ={master_lon}
ant2-pos3          ={master_alt}

inpstr1-type       =tcpcli
inpstr1-path       ={rover_ip}:{rover_port}
inpstr1-format     =ubx

inpstr2-type       =tcpcli
inpstr2-path       ={master_ip}:{master_port}
inpstr2-format     =ubx

outstr1-type       =file
outstr1-path       ={solution_path}
outstr1-format     =llh

file-tracefile     =/tmp/rt/rtkrcv_{rover_serial}_minimal.trace
"""
    
    with open(tmp_file, 'w') as f:
        f.write(config_content)
    
    print(f"\nCreato anche config MINIMALE: {tmp_file}")
    print("Usa questo per test se il config principale non funziona")
    
    return tmp_file
