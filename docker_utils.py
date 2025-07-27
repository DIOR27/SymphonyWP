import os
import subprocess
import socket
import typer


def check_docker():
    try:
        subprocess.run(["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        typer.echo("\n[!] Docker no está instalado o no está en ejecución.")
        raise typer.Exit(1)


def add_hosts_entry(site_name):
    hosts_file = "/etc/hosts"
    entry = f"127.0.0.1 {site_name}\n"
    if os.name == "nt":
        hosts_file = os.path.join(os.environ['SystemRoot'], 'System32', 'drivers', 'etc', 'hosts')

    try:
        with open(hosts_file, "r") as f:
            lines = f.readlines()
        if any(site_name in line for line in lines):
            return
        with open(hosts_file, "a") as f:
            f.write(entry)
    except PermissionError:
        typer.echo("[!] No se pudo modificar el archivo hosts. Intenta correr el script con privilegios de administrador.")


def remove_hosts_entry(site_name):
    hosts_file = "/etc/hosts"
    if os.name == "nt":
        hosts_file = os.path.join(os.environ['SystemRoot'], 'System32', 'drivers', 'etc', 'hosts')

    try:
        with open(hosts_file, "r") as f:
            lines = f.readlines()
        with open(hosts_file, "w") as f:
            for line in lines:
                if site_name not in line:
                    f.write(line)
    except PermissionError:
        typer.echo("[!] No se pudo modificar el archivo hosts. Intenta correr el script con privilegios de administrador.")


def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def generate_random_port(start=1024, end=65535):
    import random
    for _ in range(100):
        port = random.randint(start, end)
        if not is_port_in_use(port):
            return port
    raise RuntimeError("No se pudo encontrar un puerto libre después de múltiples intentos")
