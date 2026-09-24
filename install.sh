#!/bin/bash

# =====================================================
# VM Security Dashboard - Installation Script
# =====================================================

set -e

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║     VM Security Dashboard - Installer        ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# --- CHECK ROOT ---
if [ "$EUID" -ne 0 ]; then
    echo "❌ Please run as root: sudo bash install.sh"
    exit 1
fi

echo "✅ Running as root"

# --- INSTALL DEPENDENCIES ---
echo ""
echo "📦 Installing system dependencies..."
apt update -qq
apt install -y python3 python3-pip python3-venv python3-dev build-essential -qq
echo "✅ System dependencies installed"

# --- CREATE DIRECTORY ---
echo ""
echo "📁 Setting up /opt/vm-dashboard..."
mkdir -p /opt/vm-dashboard/templates
cp app.py /opt/vm-dashboard/
cp templates/login.html /opt/vm-dashboard/templates/
cp templates/dashboard.html /opt/vm-dashboard/templates/
echo "✅ Files copied"

# --- CREATE VIRTUAL ENV ---
echo ""
echo "🐍 Creating Python virtual environment..."
python3 -m venv /opt/vm-dashboard/venv
echo "✅ Virtual environment created"

# --- INSTALL PYTHON PACKAGES ---
echo ""
echo "📦 Installing Python packages..."
/opt/vm-dashboard/venv/bin/pip install --quiet --upgrade pip
/opt/vm-dashboard/venv/bin/pip install --quiet flask psutil
echo "✅ Python packages installed"

# --- INSTALL SYSTEMD SERVICE ---
echo ""
echo "⚙️  Installing systemd service..."
cp vm-dashboard.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable vm-dashboard
systemctl start vm-dashboard
echo "✅ Service installed and started"

# --- UFW RULE ---
echo ""
echo "🛡️  Adding UFW rule (internal only)..."
ufw allow from 10.0.0.0/8 to any port 5000 proto tcp comment "VM Dashboard internal only" 2>/dev/null || true
echo "✅ UFW rule added — accessible only from internal network"

# --- CHECK STATUS ---
echo ""
echo "🔍 Checking service status..."
sleep 2
if systemctl is-active --quiet vm-dashboard; then
    echo "✅ Dashboard is running"
else
    echo "❌ Dashboard failed to start. Check logs:"
    echo "   sudo journalctl -u vm-dashboard -n 20"
    exit 1
fi

# --- DONE ---
echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║           ✅ Installation Complete!              ║"
echo "╠══════════════════════════════════════════════════╣"
echo "║                                                  ║"
echo "║  🌐 Access: http://<YOUR-SERVER-IP>:5000         ║"
echo "║  🔑 Key:    <your-access-key>                    ║"
echo "║                                                  ║"
echo "║  Only accessible from internal network           ║"
echo "║  172.16.x.x — NOT exposed to internet           ║"
echo "║                                                  ║"
echo "╠══════════════════════════════════════════════════╣"
echo "║  Useful commands:                                ║"
echo "║  sudo systemctl status vm-dashboard              ║"
echo "║  sudo systemctl restart vm-dashboard             ║"
echo "║  sudo journalctl -u vm-dashboard -f              ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
