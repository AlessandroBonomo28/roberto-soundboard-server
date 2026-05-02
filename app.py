import os
import requests
import time
import shutil
from flask import Flask, render_template, request, redirect, url_for, send_from_directory

app = Flask(__name__)

DOWNLOAD_FOLDER = 'downloads'
SAVED_FOLDER = 'saved'
TTS_URL = "http://localhost:8087/audio"
TOKEN = "token1"

# Creazione cartelle se non esistono
for folder in [DOWNLOAD_FOLDER, SAVED_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

QUEUE_LEN=3
def clean_old_downloads():
    """Mantiene solo i QUEUE_LEN file più recenti nella cartella downloads."""
    files = []
    for f in os.listdir(DOWNLOAD_FOLDER):
        if f.endswith(".wav"):
            path = os.path.join(DOWNLOAD_FOLDER, f)
            files.append((path, os.path.getctime(path)))
    
    # Se sono più di QUEUE_LEN, ordina per data e cancella i più vecchi
    if len(files) > QUEUE_LEN:
        files.sort(key=lambda x: x[1])
        for i in range(len(files) - QUEUE_LEN):
            os.remove(files[i][0])

@app.route('/')
def index():
    # Lista download (max QUEUE_LEN)
    downloads = []
    for f in os.listdir(DOWNLOAD_FOLDER):
        if f.endswith(".wav"):
            downloads.append({"name": f, "time": os.path.getctime(os.path.join(DOWNLOAD_FOLDER, f))})
    downloads = sorted(downloads, key=lambda x: x['time'], reverse=True)

    # Lista salvati
    saved = []
    for f in os.listdir(SAVED_FOLDER):
        if f.endswith(".wav"):
            saved.append({"name": f, "time": os.path.getctime(os.path.join(SAVED_FOLDER, f))})
    saved = sorted(saved, key=lambda x: x['time'], reverse=True)

    return render_template('index.html', downloads=downloads, saved_files=saved)

@app.route('/generate', methods=['POST'])
def generate_audio():
    text = request.form.get('text')
    if text:
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filename = f"audio_{timestamp}.wav"
        filepath = os.path.join(DOWNLOAD_FOLDER, filename)
        
        try:
            response = requests.get(TTS_URL, params={"token": TOKEN, "text": text}, timeout=30)
            if response.status_code in [200, 202]:
                with open(filepath, "wb") as f:
                    f.write(response.content)
                clean_old_downloads() # Pulizia dopo ogni generazione
        except Exception as e:
            print(f"Errore: {e}")
    return redirect(url_for('index'))

@app.route('/save/<filename>', methods=['POST'])
def save_file(filename):
    """Copia il file da downloads a saved."""
    src = os.path.join(DOWNLOAD_FOLDER, filename)
    if os.path.exists(src):
        shutil.copy(src, os.path.join(SAVED_FOLDER, filename))
    return redirect(url_for('index'))

@app.route('/rename_saved/<old_name>', methods=['POST'])
def rename_saved(old_name):
    new_name = request.form.get('new_name').strip()
    if new_name:
        if not new_name.endswith(".wav"):
            new_name += ".wav"
        os.rename(os.path.join(SAVED_FOLDER, old_name), os.path.join(SAVED_FOLDER, new_name))
    return redirect(url_for('index'))

@app.route('/delete_saved/<filename>')
def delete_saved(filename):
    path = os.path.join(SAVED_FOLDER, filename)
    if os.path.exists(path):
        os.remove(path)
    return redirect(url_for('index'))

@app.route('/file/<folder>/<filename>')
def serve_file(folder, filename):
    target = DOWNLOAD_FOLDER if folder == 'downloads' else SAVED_FOLDER
    return send_from_directory(target, filename)

if __name__ == '__main__':
    app.run(debug=True, port=5000)