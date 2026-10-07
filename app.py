import concurrent.futures, os, socket, subprocess
from flask import Flask, render_template_string, jsonify

app = Flask(__name__)

def speak(text):
    os.system(f'termux-tts-speak "{text}" >/dev/null 2>&1')

def get_wifi_base_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        s.close()
        return ".".join(ip.split(".")[:3])
    except Exception:
        return "192.168.1"

def ping_ip(ip):
    try:
        res = subprocess.run(["ping", "-c", "1", "-W", "1", ip], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return ip if res.returncode == 0 else None
    except Exception:
        return None

def resolve_device_name(ip):
    try:
        hostname = socket.gethostbyaddr(ip)[0]
        if hostname and hostname != ip:
            return hostname.split('.')[0]
    except Exception:
        pass
    return "Appareil inconnu"

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PocketSOC OS</title>
    <style>
        body { font-family: monospace; background: #0f0f0f; color: #00ff66; padding: 20px; text-align: center; }
        h1 { border-bottom: 2px solid #00ff66; padding-bottom: 10px; }
        button { background: #00ff66; color: #000; border: none; padding: 15px 25px; font-weight: bold; font-size: 16px; border-radius: 8px; cursor: pointer; margin-top: 20px; }
        #results { margin-top: 30px; text-align: left; background: #1a1a1a; padding: 15px; border-radius: 5px; white-space: pre-wrap; font-size: 14px; }
    </style>
</head>
<body>
    <h1>=== PocketSOC OS ===</h1>
    <button onclick="startScan()">LANCER LE SCAN</button>
    <div id="status">Prêt.</div>
    <div id="results"></div>

    <script>
        function startScan() {
            document.getElementById('status').innerText = "Scan en cours...";
            document.getElementById('results').innerText = "";
            fetch('/scan')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('status').innerText = "Scan terminé !";
                    document.getElementById('results').innerText = data.text;
                });
        }
    </script>
</body>
</html>
'''

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)

@app.route('/scan')
def scan():
    base_ip = get_wifi_base_ip()
    speak("Analyse du réseau démarrée.")
    ip_list = [f"{base_ip}.{i}" for i in range(1, 255)]
    active_ips = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
        results_ping = executor.map(ping_ip, ip_list)
        for ip in results_ping:
            if ip: active_ips.append(ip)

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        names = list(executor.map(resolve_device_name, active_ips))

    output_lines = []
    speech_phrases = []

    for ip, dev_name in zip(active_ips, names):
        output_lines.append(f"IP: {ip:<15} | Nom: {dev_name}")
        spoken_ip = ip.replace(".", " point ")
        speech_phrases.append(f"Adresse {spoken_ip}, nom : {dev_name}")

    if not output_lines:
        out_text = "Aucun appareil trouvé."
        speech_text = "Aucun appareil trouvé. Fin des appareils trouvés."
    else:
        out_text = "\n".join(output_lines)
        speech_text = f"Scan terminé. {len(active_ips)} appareils trouvés : " + ". ".join(speech_phrases) + ". Fin des appareils trouvés."

    speak(speech_text)
    return jsonify({'text': out_text})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
