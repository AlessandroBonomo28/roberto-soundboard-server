import os
import requests
import time
import shutil
import subprocess  # <--- Nuovo import per i comandi shell
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename

app = Flask(__name__)

DOWNLOAD_FOLDER = 'downloads'
SAVED_FOLDER = 'saved'
TTS_URL = "http://localhost:8087/audio"
TOKEN = "token1"
QUEUE_LEN = 3
AUDIO_EXTENSIONS = ('.wav')#('.wav', '.mp3', '.ogg', '.m4a')

# Configurazione cartelle
for folder in [DOWNLOAD_FOLDER, SAVED_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

def clean_old_downloads():
    files = []
    for f in os.listdir(DOWNLOAD_FOLDER):
        if f.endswith(".wav"):
            path = os.path.join(DOWNLOAD_FOLDER, f)
            files.append((path, os.path.getctime(path)))
    if len(files) > QUEUE_LEN:
        files.sort(key=lambda x: x[1])
        for i in range(len(files) - QUEUE_LEN):
            os.remove(files[i][0])

@app.route('/')
def index():
    downloads = [{"name": f, "time": os.path.getctime(os.path.join(DOWNLOAD_FOLDER, f))} 
                 for f in os.listdir(DOWNLOAD_FOLDER) if f.endswith(".wav")]
    saved = [{"name": f, "time": os.path.getctime(os.path.join(SAVED_FOLDER, f))} 
             for f in os.listdir(SAVED_FOLDER) if f.lower().endswith(AUDIO_EXTENSIONS)]
    
    return render_template('index.html', 
                           downloads=sorted(downloads, key=lambda x: x['time'], reverse=True), 
                           saved_files=sorted(saved, key=lambda x: x['time'], reverse=True))

import platform # Aggiungi questo import in alto

@app.route('/play_hw/<folder>/<filename>')
def play_hw(folder, filename):
    target = DOWNLOAD_FOLDER if folder == 'downloads' else SAVED_FOLDER
    filepath = os.path.normpath(os.path.join(target, filename)) # Sistema i separatori / o \
    
    if not os.path.exists(filepath):
        print(f"Errore: Il file {filepath} non esiste!")
        return '', 404

    # Rileviamo il sistema operativo
    current_os = platform.system()
    
    if current_os == "Linux":
        # Se è un MP3, aplay non funzionerà. Serve un altro player come mpg123
        if filename.lower().endswith(".mp3"):
            cmd = ["mpg123", filepath]
        else:
            # Tuo comando originale per la scheda Seeed
            cmd = [
                "aplay", 
                "-D", "plughw:CARD=seeed2micvoicec,DEV=0", 
                "-r", "22050", 
                "-c", "1", 
                "-f", "S16_LE", 
                "-t", "raw", 
                filepath
            ]
    else:
        # Siamo su Windows (TEST): usiamo il comando 'start' per aprire il player di sistema
        # Questo serve solo per vedere se il pulsante funziona mentre programmi sul PC
        print(f"Running on Windows: Simulo riproduzione per {filename}")
        cmd = ["powershell", "-c", f"(New-Object Media.SoundPlayer '{filepath}').PlaySync()"]
        # Nota: il comando powershell sopra funziona solo per i .wav

    try:
        subprocess.Popen(cmd)
        print(f"Comando inviato: {' '.join(cmd)}")
    except Exception as e:
        print(f"Errore durante l'esecuzione del comando: {e}")
            
    return '', 204
# ... (restanti rotte generate, save, upload, rename, delete rimangono invariate) ...

@app.route('/generate', methods=['POST'])
def generate_audio():
    text = request.form.get('text')
    if text:
        filename = f"audio_{time.strftime('%Y%m%d-%H%M%S')}.wav"
        filepath = os.path.join(DOWNLOAD_FOLDER, filename)
        try:
            response = requests.get(TTS_URL, params={"token": TOKEN, "text": text}, timeout=30)
            if response.status_code in [200, 202]:
                with open(filepath, "wb") as f:
                    f.write(response.content)
                clean_old_downloads()
        except Exception as e:
            print(f"Errore: {e}")
    return redirect(url_for('index'))

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
    app.run(debug=True, port=5000, host='0.0.0.0') # host 0.0.0.0 per vederlo in rete