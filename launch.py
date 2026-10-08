import subprocess
import time
import webbrowser

url = "http://127.0.0.1:8000"

process = subprocess.Popen(
    ["python", "-m", "fastapi", "dev"]
)

time.sleep(2)

webbrowser.open(url)

process.wait()