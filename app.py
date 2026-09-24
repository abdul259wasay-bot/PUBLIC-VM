from flask import Flask, render_template, request, jsonify, session, redirect, url_for, Response
import subprocess
import psutil
import os
import json
import threading
import queue
import time
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET', 'change_this_secret_key')

# --- AUTH KEY — set via environment variable or change below ---
SECRET_KEY = os.environ.get('DASHBOARD_KEY', 'change_this_key')

# --- AUTH DECORATOR ---
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# --- LOGIN ---
@app.route('/', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        key = request.form.get('key', '')
        if key == SECRET_KEY:
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            error = 'Invalid key. Access denied.'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- DASHBOARD ---
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

# --- SYSTEM STATS ---
@app.route('/api/stats')
@login_required
def stats():
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    net = psutil.net_io_counters()
    boot_time = datetime.fromtimestamp(psutil.boot_time()).strftime('%Y-%m-%d %H:%M:%S')

    return jsonify({
        'cpu': cpu,
        'ram_used': round(ram.used / 1024 / 1024 / 1024, 2),
        'ram_total': round(ram.total / 1024 / 1024 / 1024, 2),
        'ram_percent': ram.percent,
        'disk_used': round(disk.used / 1024 / 1024 / 1024, 2),
        'disk_total': round(disk.total / 1024 / 1024 / 1024, 2),
        'disk_percent': disk.percent,
        'net_sent': round(net.bytes_sent / 1024 / 1024, 2),
        'net_recv': round(net.bytes_recv / 1024 / 1024, 2),
        'boot_time': boot_time,
        'uptime': str(datetime.now() - datetime.fromtimestamp(psutil.boot_time())).split('.')[0]
    })

# --- PROCESSES ---
@app.route('/api/processes')
@login_required
def processes():
    procs = []
    for p in sorted(psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']),
                    key=lambda x: x.info['cpu_percent'] or 0, reverse=True)[:20]:
        procs.append(p.info)
    return jsonify(procs)

# --- LOGS ---
def read_log(command, lines=100):
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
        return result.stdout or result.stderr or 'No output'
    except Exception as e:
        return str(e)

@app.route('/api/logs/system')
@login_required
def logs_system():
    lines = request.args.get('lines', 50)
    data = read_log(f'journalctl -n {lines} --no-pager -o short')
    return jsonify({'logs': data})

@app.route('/api/logs/mediamtx')
@login_required
def logs_mediamtx():
    lines = request.args.get('lines', 50)
    data = read_log(f'journalctl -u mediamtx -n {lines} --no-pager -o short')
    return jsonify({'logs': data})

@app.route('/api/logs/ufw')
@login_required
def logs_ufw():
    data = read_log('tail -n 100 /var/log/ufw.log')
    return jsonify({'logs': data})

@app.route('/api/logs/auth')
@login_required
def logs_auth():
    data = read_log('tail -n 100 /var/log/auth.log')
    return jsonify({'logs': data})

@app.route('/api/logs/apache')
@login_required
def logs_apache():
    data = read_log('tail -n 100 /var/log/apache2/access.log 2>/dev/null || echo "No apache logs"')
    return jsonify({'logs': data})

# --- ATTACK MONITOR ---
@app.route('/api/attacks')
@login_required
def attacks():
    # Failed SSH attempts
    ssh_fails = read_log("grep 'Failed password\|Invalid user\|authentication failure' /var/log/auth.log | tail -50")
    # Blocked by UFW
    ufw_blocks = read_log("grep 'BLOCK\|UFW' /var/log/ufw.log | tail -50")
    # Brute force count per IP
    brute_force = read_log("grep 'Failed password' /var/log/auth.log | awk '{print $(NF-3)}' | sort | uniq -c | sort -rn | head -20")
    # Recent successful logins
    success_logins = read_log("grep 'Accepted\|session opened' /var/log/auth.log | tail -20")

    return jsonify({
        'ssh_failures': ssh_fails,
        'ufw_blocks': ufw_blocks,
        'brute_force_ips': brute_force,
        'successful_logins': success_logins
    })

# --- SERVICES STATUS ---
@app.route('/api/services')
@login_required
def services():
    service_list = ['mediamtx', 'ssh', 'ufw', 'apache2', 'fail2ban', 'redis-server', 'postgresql']
    results = {}
    for svc in service_list:
        try:
            result = subprocess.run(
                f'systemctl is-active {svc}',
                shell=True, capture_output=True, text=True, timeout=5
            )
            results[svc] = result.stdout.strip()
        except:
            results[svc] = 'unknown'
    return jsonify(results)

# --- UFW STATUS ---
@app.route('/api/ufw')
@login_required
def ufw_status():
    data = read_log('ufw status verbose')
    return jsonify({'status': data})

# --- NETWORK CONNECTIONS ---
@app.route('/api/connections')
@login_required
def connections():
    data = read_log('ss -tnp | head -50')
    return jsonify({'connections': data})

# --- OPEN PORTS ---
@app.route('/api/ports')
@login_required
def ports():
    data = read_log('ss -tlnp')
    return jsonify({'ports': data})

# --- SSH TERMINAL (WebSocket-like via SSE) ---
@app.route('/api/exec', methods=['POST'])
@login_required
def execute():
    cmd = request.json.get('command', '').strip()
    # Whitelist safe commands only
    allowed_prefixes = [
        'ls', 'pwd', 'df', 'free', 'uptime', 'who', 'w',
        'ps', 'top', 'htop', 'cat /var/log', 'tail', 'grep',
        'systemctl status', 'journalctl', 'ufw status',
        'netstat', 'ss', 'ip', 'ping', 'curl ifconfig.me',
        'mediamtx', 'sudo journalctl', 'sudo ufw status',
        'sudo systemctl status', 'sudo tail', 'sudo ss',
        'sudo netstat', 'sudo ps', 'echo', 'date', 'hostname'
    ]
    allowed = any(cmd.startswith(prefix) for prefix in allowed_prefixes)
    if not allowed:
        return jsonify({'output': '⛔ Command not allowed for security reasons.', 'error': True})
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=15)
        output = result.stdout or result.stderr or '(no output)'
        return jsonify({'output': output, 'error': False})
    except subprocess.TimeoutExpired:
        return jsonify({'output': '⏱ Command timed out.', 'error': True})
    except Exception as e:
        return jsonify({'output': str(e), 'error': True})

# --- LIVE LOG STREAM (SSE) ---
@app.route('/api/stream/logs')
@login_required
def stream_logs():
    def generate():
        process = subprocess.Popen(
            ['journalctl', '-f', '-n', '0', '--no-pager'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        try:
            for line in process.stdout:
                yield f"data: {line.strip()}\n\n"
        except GeneratorExit:
            process.kill()
    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
