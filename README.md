# roberto-soundboard-server
http soundboard server for roberto rest api

<img width="700" alt="Immagine 2026-05-03 010258" src="https://github.com/user-attachments/assets/b0303c01-d0ac-4a45-9025-14f3311aca39" />

- interroga backend [restRoberto](https://github.com/TheTipo01/restRoberto)
- carica mp3 e wav e riproducili quando vuoi su server
- supporto per linux raspberry pi respeaker module (aplay per riprodurre wav e mpg123)
- salva tts recenti di roberto

## Setup
Requisiti

- installa `mpg123` per riprodurre mp3
- installa drivers per respeaker

```
python3 -m venv env
```

```
source env/bin/activate
```

``` 
pip install -r requirements
```

```
python app.py
```

e ora collegati a `hostname:5000` con un browser

## Servizi automatici


```
sudo nano /etc/systemd/system/server.service
```

```
[Unit]
Description=Foo

[Service]
ExecStart=/home/pi/roberto-soundboard-server/env/bin/python /home/pi/roberto-soundboard-server/app.py
WorkingDirectory=/home/pi/roberto-soundboard-server/
[Install]
WantedBy=multi-user.target
```

```
sudo systemctl enable server.service
```

```
sudo nano /etc/systemd/system/button.service
```

**servizio per spegnere il raspberry pi zero con il bottone integrato**

### nota
più si aggiungono suoni alla soundboard, più la pagina web diventa pesante perchè per ogni nuovo client che si collega, il raspberry deve inviare tutti i suoni salvati al client
