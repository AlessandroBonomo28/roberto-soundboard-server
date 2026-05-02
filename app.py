import os
import requests
import time
from flask import Flask, render_template, request, redirect, url_for, send_from_directory

app = Flask(__name__)

# Configurazione
DOWNLOAD_FOLDER = 'downloads'
TTS_URL = "http://localhost:8087/audio"
TOKEN = "token1"

# Assicuriamoci che la cartella download esista
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

@app.route('/')
def index():
    # Recupera i file audio e ordinali per data di creazione (più recenti in alto)
    files = []
    for filename in os.listdir(DOWNLOAD_FOLDER):
        if filename.endswith(".wav"):
            path = os.path.join(DOWNLOAD_FOLDER, filename)
            files.append({
                "name": filename,
                "time": os.path.getctime(path)
            })
    
    # Ordiniamo per timestamp decrescente
    sorted_files = sorted(files, key=lambda x: x['time'], reverse=True)
    return render_template('index.html', files=sorted_files)

@app.route('/generate', methods=['POST'])
def generate_audio():
    text = request.form.get('text')
    if not text:
        return redirect(url_for('index'))

    # Generiamo un nome file unico basato sul tempo
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    filename = f"audio_{timestamp}.wav"
    filepath = os.path.join(DOWNLOAD_FOLDER, filename)

    # Chiamata al tuo backend esistente
    params = {"token": TOKEN, "text": text}
    try:
        response = requests.get(TTS_URL, params=params, timeout=30)
        if response.status_code in [200, 202]:
            with open(filepath, "wb") as f:
                f.write(response.content)
    except Exception as e:
        print(f"Errore durante il download: {e}")

    return redirect(url_for('index'))

@app.route('/download/<filename>')
def serve_audio(filename):
    return send_from_directory(DOWNLOAD_FOLDER, filename)

if __name__ == '__main__':
    app.run(debug=True, port=5000)