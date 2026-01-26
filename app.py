"""
Flask GUI Dashboard for RTKRCV Multi Session Handler.
Provides web interface to configure receivers, launch main.py, and visualize KML results.
"""
import os
import subprocess
import threading
import queue
import glob
from pathlib import Path
from flask import Flask, render_template, jsonify, request, Response
import yaml

app = Flask(__name__)

# Global state for subprocess management
process_queue = queue.Queue()
current_process = None
process_lock = threading.Lock()

STATIONS_PATH = Path(__file__).parent / "stations.yaml"
OUTPUT_PATH = Path(__file__).parent / "output"


def load_stations():
    """Load receivers configuration from YAML."""
    if STATIONS_PATH.exists():
        with open(STATIONS_PATH, 'r') as f:
            return yaml.safe_load(f)
    return {"receivers": {}}


def save_stations(data):
    """Save receivers configuration to YAML."""
    with open(STATIONS_PATH, 'w') as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)


@app.route('/')
def index():
    """Render main dashboard."""
    return render_template('index.html')


@app.route('/api/receivers', methods=['GET'])
def get_receivers():
    """Return receivers configuration as JSON."""
    data = load_stations()
    return jsonify(data)


@app.route('/api/receivers', methods=['POST'])
def save_receivers():
    """Save receivers configuration from JSON."""
    data = request.get_json()
    save_stations(data)
    return jsonify({"status": "ok"})


@app.route('/api/start', methods=['POST'])
def start_process():
    """Launch main.py as subprocess."""
    global current_process
    import shutil
    
    with process_lock:
        if current_process and current_process.poll() is None:
            return jsonify({"status": "error", "message": "Process already running"}), 400
        
        # Clean output/ and tmp/ folders
        for folder in [OUTPUT_PATH, Path(__file__).parent / "tmp"]:
            if folder.exists():
                for file in folder.iterdir():
                    if file.is_file():
                        file.unlink()
        
        # Clear the queue
        while not process_queue.empty():
            try:
                process_queue.get_nowait()
            except queue.Empty:
                break
        
        # Set environment for unbuffered Python output
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'
        
        # Start main.py subprocess with unbuffered output
        current_process = subprocess.Popen(
            ["python", "-u", "main.py"],  # -u forces unbuffered stdout/stderr
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,  # Line buffered
            cwd=Path(__file__).parent,
            env=env
        )
        
        # Start thread to read output line by line
        def read_output():
            try:
                for line in iter(current_process.stdout.readline, ''):
                    if line:
                        process_queue.put(line)
                    if current_process.poll() is not None:
                        break
            finally:
                current_process.stdout.close()
                process_queue.put(None)  # Signal end of stream
        
        thread = threading.Thread(target=read_output, daemon=True)
        thread.start()
        
        return jsonify({"status": "started"})


@app.route('/api/stream')
def stream_output():
    """SSE endpoint for real-time process output."""
    def generate():
        while True:
            try:
                line = process_queue.get(timeout=30)
                if line is None:
                    # Process finished
                    yield f"data: [PROCESS_END]\n\n"
                    break
                yield f"data: {line}\n\n"
            except queue.Empty:
                # Send heartbeat to keep connection alive
                yield f"data: \n\n"
    
    response = Response(generate(), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'  # Disable nginx buffering
    response.headers['Connection'] = 'keep-alive'
    return response


@app.route('/api/stop', methods=['POST'])
def stop_process():
    """Terminate the running subprocess."""
    global current_process
    
    with process_lock:
        if current_process and current_process.poll() is None:
            current_process.terminate()
            try:
                current_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                current_process.kill()
            process_queue.put(None)  # Signal end of stream
            return jsonify({"status": "stopped"})
        else:
            return jsonify({"status": "error", "message": "No process running"}), 400


@app.route('/api/kml')
def get_latest_kml():
    """Return the most recent KML file content with timestamp filename."""
    from datetime import datetime
    
    kml_files = glob.glob(str(OUTPUT_PATH / "*.kml"))
    if not kml_files:
        return jsonify({"status": "error", "message": "No KML files found"}), 404
    
    # Get most recent by modification time
    latest_kml = max(kml_files, key=os.path.getmtime)
    
    with open(latest_kml, 'r') as f:
        content = f.read()
    
    # Generate timestamp filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}.kml"
    
    response = Response(content, mimetype='application/vnd.google-earth.kml+xml')
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@app.route('/api/kml/json')
def get_kml_as_json():
    """Parse KML and return coordinates as JSON for Leaflet."""
    import xml.etree.ElementTree as ET
    
    kml_files = glob.glob(str(OUTPUT_PATH / "*.kml"))
    if not kml_files:
        return jsonify({"status": "error", "message": "No KML files found"}), 404
    
    latest_kml = max(kml_files, key=os.path.getmtime)
    
    tree = ET.parse(latest_kml)
    root = tree.getroot()
    
    # KML namespace
    ns = {'kml': 'http://www.opengis.net/kml/2.2'}
    
    placemarks = []
    for placemark in root.findall('.//kml:Placemark', ns):
        name = placemark.find('kml:name', ns)
        desc = placemark.find('kml:description', ns)
        coords = placemark.find('.//kml:coordinates', ns)
        style = placemark.find('kml:styleUrl', ns)
        
        if coords is not None:
            lon, lat, alt = coords.text.strip().split(',')
            placemarks.append({
                'name': name.text if name is not None else 'Unknown',
                'description': desc.text if desc is not None else '',
                'lat': float(lat),
                'lon': float(lon),
                'alt': float(alt),
                'style': style.text if style is not None else ''
            })
    
    return jsonify({"placemarks": placemarks, "file": Path(latest_kml).name})


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000, threaded=True)
