#!/bin/bash

echo "[*] Instalador de SymphonyWP CLI"

# Paso 1: Instalar pipx si no existe
if ! command -v pipx &> /dev/null; then
    echo "[*] pipx no está instalado. Instalando..."

    if [ -f /etc/debian_version ]; then
        sudo apt update
        sudo apt install -y pipx python3-venv
    elif [ "$(uname)" == "Darwin" ]; then
        # macOS
        if ! command -v brew &> /dev/null; then
            echo "[!] Homebrew no está instalado. Por favor instala brew primero: https://brew.sh"
            exit 1
        fi
        brew install pipx
    else
        echo "[!] Sistema operativo no compatible. Instala pipx manualmente."
        exit 1
    fi
fi

# Paso 2: Asegurar que ~/.local/bin esté en el PATH
echo "[*] Ejecutando pipx ensurepath..."
pipx ensurepath

# Intentar recargar el PATH temporalmente
export PATH="$HOME/.local/bin:$PATH"

# Paso 3: Instalar symphony local
echo "[*] Instalando SymphonyWP..."
pipx install .

# Paso 4: Confirmar instalación
echo "[*] Verificando instalación..."
if command -v symphony &> /dev/null; then
    echo "[+] ¡Instalación completada con éxito! Ejecuta 'symphony --help' para comenzar."
else
    echo "[!] symphony no está disponible aún. Reinicia tu terminal o ejecuta: source ~/.bashrc"
fi
