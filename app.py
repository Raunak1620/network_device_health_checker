import os
import paramiko
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

# Directory to store health reports
REPORTS_DIR = "reports"
os.makedirs(REPORTS_DIR, exist_ok=True)

def connect_to_device(host, username, password):
    try:
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(hostname=host, username=username, password=password)
        return ssh_client
    except Exception as e:
        print(f"Error connecting to {host}: {e}")
        return None

def run_command(ssh_client, command):
    try:
        stdin, stdout, stderr = ssh_client.exec_command(command)
        return stdout.read().decode('utf-8')
    except Exception as e:
        print(f"Error running command {command}: {e}")
        return None

def check_device_health(host, username, password, device_type):
    ssh_client = connect_to_device(host, username, password)
    if not ssh_client:
        return

    health_data = {}

    if device_type == "cisco":
        commands = {
            "CPU_Usage": "show processes cpu | include CPU utilization",
            "Memory_Usage": "show processes memory | include Used",
            "Interfaces": "show ip interface brief",
            "Temperature": "show environment temperature"
        }
    elif device_type == "paloalto":
        commands = {
            "CPU_Usage": "show system resources | match CPU",
            "Memory_Usage": "show system resources | match Mem",
            "Interfaces": "show interface all",
            "Temperature": "show system environmentals"
        }
    else:
        return {"error": "Unsupported device type"}

    for key, command in commands.items():
        output = run_command(ssh_client, command)
        if output:
            health_data[key] = output.strip()

    ssh_client.close()
    return health_data

def save_health_report(device_name, health_data):
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = os.path.join(REPORTS_DIR, f"{device_name}_health_report_{timestamp}.txt")

    with open(filename, 'w') as file:
        file.write(f"Health Report for {device_name} ({timestamp})\n")
        file.write("=" * 50 + "\n")
        for key, value in health_data.items():
            file.write(f"{key}:\n{value}\n\n")

    return filename

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/health_check', methods=['POST'])
def health_check():
    data = request.json
    host = data.get('host')
    username = data.get('username')
    password = data.get('password')
    device_type = data.get('device_type')

    health_data = check_device_health(host, username, password, device_type)
    if health_data:
        save_health_report(host, health_data)
        return jsonify(health_data)
    else:
        return jsonify({"error": "Failed to collect health data."}), 500

if __name__ == "__main__":
    app.run(debug=True)
