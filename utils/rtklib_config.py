from pathlib import Path
import tempfile

def generate_rtkrcv_config(rover_serial: str, rover_ip: str, rover_port: int,
                          master_ip: str, master_port: int,
                          master_lat: float, master_lon: float, master_alt: float) -> Path:
    """Genera file di configurazione per RTKRCV"""
    
    tmp_file = Path(tempfile.gettempdir()) / f"rtkrcv_{rover_serial}.conf"
    solution_path = Path(tempfile.gettempdir()) / f"solution_{rover_serial}.pos"
    trace_path = Path(tempfile.gettempdir()) / f"rtkrcv_trace_{rover_serial}.log"
    
    config_content = f"""# RTKRCV Configuration
console-passwd=admin
console-timetype   =utc # (0:gpst,1:utc,2:jst,3:tow)
console-soltype    =dms # (0:dms,1:deg,2:xyz,3:enu,4:pyl)
console-solflag    =off # (0:off,1:std+2:age/ratio/ns)
console-dev        =     # no console device needed
#
# OPTIONS 1
pos1-posmode       =static-start     # (0:single,1:dgps,2:kinematic,3:static,4:movingbase,5:fixed,6:ppp-kine,7:ppp-static) static-start is from rtklibexplorer
pos1-frequency     =l1         # (1:l1,2:l1+l2,3:l1+l2+l5,4:l1+l2+l5+l6,5:l1+l2+l5+l6+l7)
pos1-soltype       =forward    # (0:forward,1:backward,2:combined)
pos1-elmask        =15         # (deg)
pos1-snrmask_r     =on         # (0:off,1:on)
pos1-snrmask_b     =on         # (0:off,1:on)
pos1-snrmask_L1    =20,20,20,20,20,20,20,20,20
pos1-snrmask_L2    =0,0,0,0,0,0,0,0,0
pos1-snrmask_L5    =0,0,0,0,0,0,0,0,0
pos1-dynamics      =on         # (0:off,1:on)
pos1-tidecorr      =off        # (0:off,1:on,2:otl)
pos1-ionoopt       =brdc       # (0:off,1:brdc,2:sbas,3:dual-freq,4:est-stec,5:ionex-tec,6:qzs-brdc,7:qzs-lex,8:vtec_sf,9:vtec_ef,10:gtec)
pos1-tropopt       =saas       # (0:off,1:saas,2:sbas,3:est-ztd,4:est-ztdgrad)
pos1-sateph        =brdc       # (0:brdc,1:precise,2:brdc+sbas,3:brdc+ssrapc,4:brdc+ssrcom)
pos1-posopt1       =off        # (0:off,1:on)
pos1-posopt2       =off        # (0:off,1:on)
pos1-posopt3       =off        # (0:off,1:on)
pos1-posopt4       =off        # (0:off,1:on)
pos1-posopt5       =off        # (0:off,1:on)
pos1-exclsats      =           # (prn ...)
pos1-navsys        =13         # (1:gps+2:sbas+4:glo+8:gal+16:qzs+32:comp, all=63) #13 gps+glo+gal
#
# OPTIONS 2
pos2-armode        =fix-and-hold # (0:off,1:continuous,2:instantaneous,3:fix-and-hold)
pos2-gloarmode     =off # (0:off,1:on,2:autocal)
pos2-arfilter      =on           # hint by rtklibexplorer on, default off
pos2-bdsarmode     =off          # (0:off,1:on)
pos2-arlockcnt     =0            # hint by rtklibexplorer, default 0
pos2-arthres       =3            # hint by rtklibexplorer 0.004, default 3
pos2-arthres1      =0.99
pos2-arthres2      =-0.055
pos2-arthres3      =1E-7
pos2-arthres4      =1E-3
pos2-minfixsats    =4
pos2-minholdsats   =5
pos2-arelmask      =0         # (deg) 15 hint by rtklibexplorer, default 0
pos2-aroutcnt      =5         # up to 2018/11/10 set to 100, default
pos2-arminfix      =0         # up to 2018/11/10 set to 100, default 10
pos2-armaxiter     =1
pos2-elmaskhold    =0          # (deg) hint by rtklibexplorer, default 0
pos2-slipthres     =0.05       # (m)
pos2-maxage        =100        # (s)
pos2-syncsol       =off        # (0:off,1:on)
pos2-rejionno      =1000       # (m)
pos2-rejgdop       =30
pos2-niter         =1
pos2-baselen       =0          # (m)
pos2-basesig       =0          # (m)
#
# OUTPUT DETAILS
out-solformat      =llh        # (0:llh,1:xyz,2:enu,3:nmea)
out-outhead        =on         # (0:off,1:on)
out-outopt         =off        # (0:off,1:on)
out-timesys        =gpst       # (0:gpst,1:utc,2:jst)
out-timeform       =hms        # (0:tow,1:hms)
out-timendec       =3
out-degform        =deg        # (0:deg,1:dms)
out-fieldsep       =
out-height         =ellipsoidal # (0:ellipsoidal,1:geodetic)
out-geoid          =internal   # (0:internal,1:egm96,2:egm08_2.5,3:egm08_1,4:gsi2000)
out-solstatic      =all        # (0:all,1:single)
out-nmeaintv1      =1          # (s)
out-nmeaintv2      =1          # (s)
out-outstat        =off        # (0:off,1:state,2:residual)
out-outsingle      =on         # needed to send NMEA to the Master
#
# STATISTICS
stats-eratio1      =300
stats-eratio2      =100
stats-errphase     =0.003      # (m)
stats-errphaseel   =0.003      # (m)
stats-errphasebl   =0          # (m/10km)
stats-errdoppler   =10         # (Hz)
stats-stdbias      =30         # (m)
stats-stdiono      =0.03       # (m)
stats-stdtrop      =0.3        # (m)
stats-prnaccelh    =1          # (m/s^2)
stats-prnaccelv    =1          # (m/s^2)
stats-prnbias      =0.0001     # (m)
stats-prniono      =0.001      # (m)
stats-prntrop      =0.0001     # (m)
stats-clkstab      =5e-12      # (s/s)
#
# MASTER DETAILS
ant2-postype       =llh       # (0:llh,1:xyz,2:single,3:posfile,4:rinexhead,5:rtcm)
ant2-pos1={master_lat}        # (deg|m)  LAT
ant2-pos2={master_lon}        # (deg|m)  LON
ant2-pos3={master_alt}        # (m|m)    H
ant2-anttype       =
ant2-antdele       =0          # (m)
ant2-antdeln       =0          # (m)
ant2-antdelu       =0          # (m)
#
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

# Misc settings
misc-svrcycle      =10         # (ms)
misc-timeout       =30000      # (ms)
misc-reconnect     =30000      # (ms)
misc-nmeacycle     =5000       # (ms)
misc-buffsize      =32768      # (bytes)
misc-navmsgsel     =all        # (0:all,1:rover,2:base,3:corr)

# File paths (empty = not used)
file-satantfile    =
file-rcvantfile    =
file-staposfile    =
file-geoidfile     =
file-dcbfile       =
file-tempdir       =
file-geexefile     =
file-solstatfile   =
file-tracefile     ={trace_path}
"""

    try:
        with open(tmp_file, 'w') as f:
            f.write(config_content)
        print(f"File di configurazione scritto: {tmp_file}")
        print(f"D:imensione file: {tmp_file.stat().st_size} bytes")
    except Exception as e:
        print(f"ERRORE nella scrittura del file di configurazione: {e}")
        raise

    return tmp_file
