#!/usr/bin/env bash
set -e

echo "=== Installing dependencies for Godot Bundle System ==="

# Check OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    PKG_MANAGER="apt-get"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    PKG_MANAGER="brew"
else
    echo "Unsupported OS: $OSTYPE"
    exit 1
fi

# Install Go if not present
if ! command -v go &> /dev/null; then
    echo "Installing Go..."
    if [[ "$PKG_MANAGER" == "apt-get" ]]; then
        wget -O - https://go.dev/dl/go1.21.5.linux-amd64.tar.gz | sudo tar -C /usr/local -xzf -
        export PATH=$PATH:/usr/local/go/bin
        echo 'export PATH=$PATH:/usr/local/go/bin' >> ~/.bashrc
    elif [[ "$PKG_MANAGER" == "brew" ]]; then
        brew install go
    fi
    echo "✓ Go installed"
else
    echo "✓ Go already installed: $(go version)"
fi

# Install Python3 and required packages
if ! command -v python3 &> /dev/null; then
    echo "Installing Python3..."
    if [[ "$PKG_MANAGER" == "apt-get" ]]; then
        sudo apt-get update
        sudo apt-get install -y python3 python3-pip
    elif [[ "$PKG_MANAGER" == "brew" ]]; then
        brew install python3
    fi
    echo "✓ Python3 installed"
else
    echo "✓ Python3 already installed: $(python3 --version)"
fi

# Install PHP if not present
if ! command -v php &> /dev/null; then
    echo "Installing PHP..."
    if [[ "$PKG_MANAGER" == "apt-get" ]]; then
        sudo apt-get install -y php php-cli
    elif [[ "$PKG_MANAGER" == "brew" ]]; then
        brew install php
    fi
    echo "✓ PHP installed"
else
    echo "✓ PHP already installed: $(php --version | head -n 1)"
fi

# Install Docker if not present
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    if [[ "$PKG_MANAGER" == "apt-get" ]]; then
        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh
        sudo usermod -aG docker $USER
        rm get-docker.sh
    elif [[ "$PKG_MANAGER" == "brew" ]]; then
        brew install --cask docker
    fi
    echo "✓ Docker installed (you may need to log out and back in for group changes)"
else
    echo "✓ Docker already installed: $(docker --version)"
fi

# Install Docker Compose if not present
if ! command -v docker-compose &> /dev/null; then
    echo "Installing Docker Compose..."
    if [[ "$PKG_MANAGER" == "apt-get" ]]; then
        sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
    elif [[ "$PKG_MANAGER" == "brew" ]]; then
        brew install docker-compose
    fi
    echo "✓ Docker Compose installed"
else
    echo "✓ Docker Compose already installed: $(docker-compose --version)"
fi

# Install Go dependencies
echo "Installing Go dependencies..."
cd "$(dirname "$0")/.."
if [ -f "go.mod" ]; then
    go mod download
    echo "✓ Go dependencies downloaded"
else
    echo "⚠ go.mod not found, skipping Go dependencies"
fi

echo ""
echo "=== Installation complete ==="
echo "Please run 'source ~/.bashrc' or log out and back in for PATH changes to take effect"
