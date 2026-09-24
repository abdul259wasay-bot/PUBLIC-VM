# VM Security Dashboard

> A lightweight, self-hosted SOC-style monitoring panel for Ubuntu servers.
> Built with Python Flask. Secured with an access key. Runs on your own infrastructure.

![Python](https://img.shields.io/badge/Python-3.8+-blue)
![Flask](https://img.shields.io/badge/Flask-3.0-lightgrey)
![Platform](https://img.shields.io/badge/platform-Ubuntu-orange)
![License](https://img.shields.io/badge/license-MIT-green)
![Internal](https://img.shields.io/badge/access-internal%20only-red)

---

## What is this?

VM Security Dashboard is a real-time browser-based monitoring panel for Linux servers. It gives you full visibility into your machine — system health, running processes, firewall activity, authentication logs, and live event streams — all from a clean dark-themed web UI.

No heavyweight tools. No database. No external dependencies beyond Flask and psutil. One command to install.

---

## Screenshots

### Overview — System Health at a Glance
![Overview](screenshots/overview.png)

The main dashboard shows six live metric cards across the top: **CPU Usage**, **RAM Usage**, **Disk Usage**, **Network Sent**, **Network Received**, and **Uptime**. Each card updates in real time. Below the cards, the **Top Processes** table lists the 20 most CPU-intensive processes with their PID, name, CPU%, memory%, and status. The green `LIVE` indicator in the top-right confirms the connection is active.

---

### Attack Monitor — Threat Intelligence
![Attack Monitor](screenshots/attacks.png)

The most security-critical panel. Divided into four sections:
- **Failed SSH Attempts** — raw auth log entries showing failed login events with timestamps, source details, and PAM messages
- **Brute Force IPs** — ranked list of IPs by number of failed attempts
- **UFW Blocked Connections** — live firewall block log showing blocked packets with source IP, destination, protocol, and packet flags
- **Successful Logins** — CRON and session open events confirming who actually got in and when

This panel tells you immediately if someone is actively trying to break into your server.

---

### Secure Terminal — Browser CLI
![Terminal](screenshots/terminal.png)

A browser-based terminal that runs directly on the server. The terminal header shows the machine hostname. A **"Safe commands only"** badge confirms the whitelist is active — only pre-approved read-only commands can execute. Quick command buttons at the bottom give one-click access to common diagnostics: Public IP, Uptime, Disk, Memory, Open Ports, MediaMTX, UFW, Who, Processes, Journal, IP Address, and Hostname.

No write access. No destructive commands. Designed for fast diagnostics without opening SSH.

---

### Live System Log Stream
![Live Stream](screenshots/live.png)

Real-time log streaming directly from `journalctl -f` using Server-Sent Events. No polling — the browser receives new log lines instantly as they appear. The **STREAMING** badge confirms the SSE connection is live. Pause and Clear buttons let you stop the stream or wipe the view. Useful for watching what your server is doing in real time.

---

## Features

| Panel | What it shows |
|---|---|
| Overview | CPU, RAM, disk, network I/O, uptime, top 20 processes |
| Logs | System journal, UFW firewall, auth, Apache, MediaMTX |
| Attack Monitor | SSH brute force, failed logins, UFW blocks, successful logins |
| Services | Live status of SSH, UFW, Fail2ban, MediaMTX, Apache, Redis, PostgreSQL |
| Network | Open ports and active TCP connections via `ss` |
| Terminal | Whitelisted browser terminal with quick command buttons |
| Live Stream | Real-time `journalctl -f` via SSE — no polling |

---

## Security Model

- **Access key login** — set your own key, no user accounts needed
- **Internal network only** — UFW blocks port 5000 from the internet
- **Terminal whitelist** — only approved read-only commands can run
- **No persistent storage** — no database, nothing written to disk by the app
- **Session auth** — session expires when browser closes

This panel is designed for internal network use only. Never expose port 5000 to the internet.

---

## Requirements

- Ubuntu 20.04 / 22.04 / 24.04
- Python 3.8+
- Root or sudo access (for reading system logs)

---

## Installation

### One-command install

```bash
git clone https://github.com/abdul259wasay-bot/PUBLIC-VM
cd PUBLIC-VM
sudo bash install.sh
```

The installer:
1. Installs Python + system dependencies
2. Copies files to `/opt/vm-dashboard/`
3. Creates a Python virtual environment
4. Installs Flask and psutil
5. Registers and starts a systemd service
6. Adds a UFW rule restricting access to internal network

### Manual install

```bash
pip3 install flask psutil
python3 app.py
```

---

## Configuration

Set your access key via environment variable:

```bash
export DASHBOARD_KEY="your-strong-key-here"
export FLASK_SECRET="your-flask-secret-here"
python3 app.py
```

Or edit `app.py` directly:

```python
SECRET_KEY = os.environ.get('DASHBOARD_KEY', 'change_this_key')
```

---

## Access

```
http://<your-server-ip>:5000
```

Enter your access key. Session is valid until browser closes or you click Logout.

---

## Managing the Service

```bash
sudo systemctl status vm-dashboard
sudo systemctl restart vm-dashboard
sudo systemctl stop vm-dashboard
sudo journalctl -u vm-dashboard -f
```

---

## UFW Setup

```bash
# Block from internet
sudo ufw deny 5000

# Allow from your internal network only
sudo ufw allow from <YOUR-INTERNAL-SUBNET> to any port 5000 proto tcp
```

---

## Project Structure

```
PUBLIC-VM/
├── app.py                  # Flask backend — all routes and API
├── install.sh              # One-click installer
├── vm-dashboard.service    # Systemd service definition
├── requirements.txt        # Python dependencies
├── README.md
├── screenshots/
│   ├── overview.png        # System stats overview
│   ├── attacks.png         # Attack monitor / threat intel
│   ├── terminal.png        # Secure browser terminal
│   ├── live.png            # Live log stream
│   ├── logs.png            # Log viewer
│   ├── services.png        # Services status
│   └── network.png         # Network connections
└── templates/
    ├── login.html          # Access key login
    └── dashboard.html      # Main dashboard UI
```

---

## API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/api/stats` | GET | CPU, RAM, disk, network, uptime |
| `/api/processes` | GET | Top 20 processes by CPU |
| `/api/logs/system` | GET | System journal |
| `/api/logs/auth` | GET | Auth log |
| `/api/logs/ufw` | GET | UFW firewall log |
| `/api/logs/mediamtx` | GET | MediaMTX service log |
| `/api/logs/apache` | GET | Apache access log |
| `/api/attacks` | GET | SSH failures, brute force IPs, UFW blocks |
| `/api/services` | GET | Service status for 7 services |
| `/api/connections` | GET | Active TCP connections |
| `/api/ports` | GET | Open listening ports |
| `/api/exec` | POST | Execute whitelisted command |
| `/api/stream/logs` | GET | SSE real-time log stream |

All endpoints require a valid session.

---

## Tech Stack

- **Python 3** + **Flask** — backend and REST API
- **psutil** — system metrics collection
- **systemd** — service management integration
- **Server-Sent Events** — real-time log streaming without WebSockets
- **Vanilla JS** — frontend, zero frameworks, zero build tools

---

*Built for personal infrastructure. Keep port 5000 internal.*
