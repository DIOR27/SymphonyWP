Write-Host "[*] Instalador de SymphonyWP CLI (Windows)" -ForegroundColor Cyan

# Verificar que Python esté disponible
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "[!] Python no está instalado. Por favor instálalo desde https://www.python.org/downloads/" -ForegroundColor Red
    exit 1
}

# Verificar si pipx ya está instalado
if (-not (Get-Command pipx -ErrorAction SilentlyContinue)) {
    Write-Host "[*] pipx no está instalado. Intentando instalar..."

    if (Get-Command winget -ErrorAction SilentlyContinue) {
        winget install --id=PyPa.Pipx -e
    } elseif (Get-Command choco -ErrorAction SilentlyContinue) {
        choco install pipx -y
    } else {
        Write-Host "[!] No se encontró ni winget ni choco. Instala pipx manualmente: https://pypa.github.io/pipx/" -ForegroundColor Red
        exit 1
    }
}

# Asegurar que pipx esté en el PATH
$pipxPath = "$env:USERPROFILE\.local\bin"
if (-not ($env:PATH -like "*$pipxPath*")) {
    $env:PATH += ";$pipxPath"
}

# Ejecutar pipx ensurepath
Write-Host "[*] Ejecutando pipx ensurepath..."
pipx ensurepath | Out-Null

# Verificar que estamos en el directorio del proyecto
if (-not (Test-Path ".\setup.py")) {
    Write-Host "[!] Este script debe ejecutarse desde la carpeta del proyecto SymphonyWP." -ForegroundColor Yellow
    exit 1
}

# Instalar el CLI local
Write-Host "[*] Instalando SymphonyWP con pipx..."
pipx install .

# Verificar si el comando funciona
if (Get-Command symphony -ErrorAction SilentlyContinue) {
    Write-Host "[+] ¡Instalación completada! Puedes ejecutar 'symphony --help'" -ForegroundColor Green
} else {
    Write-Host "[!] 'symphony' no está disponible aún. Reinicia PowerShell o añade manualmente '$pipxPath' al PATH." -ForegroundColor Yellow
}
