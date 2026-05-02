import os
import requests
import time
import shutil
import subprocess
import json
import platform
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename

app = Flask(__name__)
current_audio_process = None
# Configurazione Cartelle
DOWNLOAD_FOLDER = 'downloads'
SAVED_FOLDER = 'saved'
SETTINGS_FILE = 'settings.json'
QUEUE_LEN = 3

# Aggiunto .mp3 alla tupla delle estensioni valide
AUDIO_EXTENSIONS = ('.wav', '.mp3')

for folder in [DOWNLOAD_FOLDER, SAVED_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# --- GESTIONE SETTINGS ---
def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        defaults = {
            "ip": "localhost",
            "port": "8087",
            "token": "token1"
        }
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(defaults, f, indent=4)
        return defaults
    with open(SETTINGS_FILE, 'r') as f:
        return json.load(f)

def save_settings(ip, port, token):
    settings = {"ip": ip, "port": port, "token": token}
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=4)

# --- LOGICA DOWNLOAD ---
def clean_old_downloads():
    files = []
    for f in os.listdir(DOWNLOAD_FOLDER):
        # Utilizza AUDIO_EXTENSIONS per gestire più formati, se necessario
        if f.lower().endswith(AUDIO_EXTENSIONS):
            path = os.path.join(DOWNLOAD_FOLDER, f)
            files.append((path, os.path.getctime(path)))
    if len(files) > QUEUE_LEN:
        files.sort(key=lambda x: x[1])
        for i in range(len(files) - QUEUE_LEN):
            os.remove(files[i][0])

@app.route('/')
def index():
    settings = load_settings()
    downloads = [{"name": f, "time": os.path.getctime(os.path.join(DOWNLOAD_FOLDER, f))} 
                 for f in os.listdir(DOWNLOAD_FOLDER) if f.lower().endswith(AUDIO_EXTENSIONS)]
    saved = [{"name": f, "time": os.path.getctime(os.path.join(SAVED_FOLDER, f))} 
             for f in os.listdir(SAVED_FOLDER) if f.lower().endswith(AUDIO_EXTENSIONS)]
    
    return render_template('index.html', 
                           settings=settings,
                           downloads=sorted(downloads, key=lambda x: x['time'], reverse=True), 
                           saved_files=sorted(saved, key=lambda x: x['time'], reverse=True))

@app.route('/update_settings', methods=['POST'])
def update_settings():
    ip = request.form.get('ip')
    port = request.form.get('port')
    token = request.form.get('token')
    save_settings(ip, port, token)
    return redirect(url_for('index'))

@app.route('/generate', methods=['POST'])
def generate_audio():
    text = request.form.get('text')
    settings = load_settings()
    # Costruiamo l'URL dinamicamente dai settings
    tts_url = f"http://{settings['ip']}:{settings['port']}/audio"
    
    if text:
        filename = f"audio_{time.strftime('%Y%m%d-%H%M%S')}.wav"
        filepath = os.path.join(DOWNLOAD_FOLDER, filename)
        try:
            response = requests.get(tts_url, params={"token": settings['token'], "text": text}, timeout=30)
            if response.status_code in [200, 202]:
                with open(filepath, "wb") as f:
                    f.write(response.content)
                clean_old_downloads()
        except Exception as e:
            print(f"Errore TTS: {e}")
    return redirect(url_for('index'))

@app.route('/play_hw/<folder>/<filename>')
def play_hw(folder, filename):
    global current_audio_process # Accediamo alla variabile globale
    
    target = DOWNLOAD_FOLDER if folder == 'downloads' else SAVED_FOLDER
    filepath = os.path.normpath(os.path.join(target, filename))
    
    if not os.path.exists(filepath):
        return '', 404

    # --- LOGICA DI INTERRUZIONE ---
    # Se esiste un processo ed è ancora in esecuzione (poll() == None), lo terminiamo
    if current_audio_process is not None and current_audio_process.poll() is None:
        try:
            print("Interruzione riproduzione precedente...")
            current_audio_process.terminate() # Invia SIGTERM
            current_audio_process.wait(timeout=2) # Attende che si chiuda davvero
        except Exception as e:
            print(f"Errore durante l'interruzione: {e}")
            current_audio_process.kill() # Forza la chiusura se terminate non basta

    current_os = platform.system()
    ext = os.path.splitext(filepath)[1].lower()

    if current_os == "Linux":
        if ext == '.mp3':
            cmd = ["mpg123", "-a", "plughw:CARD=seeed2micvoicec,DEV=0", filepath]
        else:
            cmd = ["aplay", "-D", "plughw:CARD=seeed2micvoicec,DEV=0", filepath]
    else:
        # Nota: Powershell PlaySync() è bloccante, meglio usare un comando che non aspetti la fine
        # o accettare che su Windows il comportamento possa differire.
        cmd = ["powershell", "-c", f"(New-Object Media.SoundPlayer '{filepath}').Play()"]

    try:
        # Avviamo il nuovo processo e salviamo il riferimento
        current_audio_process = subprocess.Popen(cmd)
        print(f"Inizio riproduzione: {filename}")
    except Exception as e:
        print(f"Errore Play: {e}")
            
    return '', 204

@app.route('/stop_audio')
def stop_audio():
    global current_audio_process
    if current_audio_process is not None and current_audio_process.poll() is None:
        current_audio_process.terminate()
        print("Audio stoppato manualmente.")
    return '', 204

@app.route('/save/<filename>', methods=['POST'])
def save_file(filename):
    src = os.path.join(DOWNLOAD_FOLDER, filename)
    if os.path.exists(src):
        shutil.copy(src, os.path.join(SAVED_FOLDER, filename))
    return redirect(url_for('index'))

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'audio_file' in request.files:
        file = request.files['audio_file']
        if file.filename != '':
            file.save(os.path.join(SAVED_FOLDER, secure_filename(file.filename)))
    return redirect(url_for('index'))

@app.route('/rename_saved/<old_name>', methods=['POST'])
def rename_saved(old_name):
    new_name = request.form.get('new_name').strip()
    if new_name:
        _, ext = os.path.splitext(old_name)
        if not os.path.splitext(new_name)[1]: new_name += ext
        os.rename(os.path.join(SAVED_FOLDER, old_name), os.path.join(SAVED_FOLDER, new_name))
    return redirect(url_for('index'))

@app.route('/delete_saved/<filename>')
def delete_saved(filename):
    path = os.path.join(SAVED_FOLDER, filename)
    if os.path.exists(path): os.remove(path)
    return redirect(url_for('index'))

@app.route('/file/<folder>/<filename>')
def serve_file(folder, filename):
    target = DOWNLOAD_FOLDER if folder == 'downloads' else SAVED_FOLDER
    return send_from_directory(target, filename)

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')