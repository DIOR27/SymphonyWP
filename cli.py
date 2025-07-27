import builtins
import os
import shutil
import json
import subprocess
import webbrowser
import platform
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
import typer
from docker_utils import check_docker, generate_random_port

app = typer.Typer()

BASE_DIR = Path(__file__).resolve().parent
SITES_DIR = BASE_DIR / "sites"
TEMPLATES_DIR = BASE_DIR / "templates"
CONFIG_FILE = BASE_DIR / "config.json"
HOSTCTL_SCRIPT = str(BASE_DIR / "hostctl.py")

TEMPLATES_DIR.mkdir(exist_ok=True)
SITES_DIR.mkdir(exist_ok=True)


def elevate_and_run(args):
    if platform.system() == "Windows":
        subprocess.run([
            "powershell", "-Command",
            f"Start-Process python -ArgumentList {','.join(repr(a) for a in args)} -Verb RunAs"
        ])
    else:
        subprocess.run(["sudo", "python3"] + args)


def load_config():
    if not CONFIG_FILE.exists():
        return {}
    with builtins.open(CONFIG_FILE) as f:
        return json.load(f)

def save_config(data):
    with builtins.open(CONFIG_FILE, 'w') as f:
        json.dump(data, f, indent=4)


@app.command()
def create(name: str, webserver: str = typer.Option("apache", help="Tipo de servidor web: apache o nginx")):
    check_docker()
    if webserver not in ["apache", "nginx"]:
        typer.echo("\n[!] El tipo de servidor debe ser 'apache' o 'nginx'.")
        raise typer.Exit(1)

    site_path = SITES_DIR / name
    if site_path.exists():
        typer.echo(f"\n[!] La instancia '{name}' ya existe.")
        raise typer.Exit(1)

    typer.echo(f"\n[*] Creando instancia '{name}' con servidor '{webserver}'...")
    site_path.mkdir(parents=True)

    port = generate_random_port()
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    template = env.get_template(f"docker-compose-{webserver}.j2")
    output = template.render(site_name=name, port=port)

    with builtins.open(site_path / "docker-compose.yml", "w") as f:
        f.write(output)

        if webserver == "nginx":
            nginx_conf_dir = site_path / "nginx" / "conf.d"
            nginx_conf_dir.mkdir(parents=True, exist_ok=True)
            nginx_template = env.get_template("nginx/default.conf.j2")
            nginx_output = nginx_template.render()
            with builtins.open(nginx_conf_dir / "default.conf", "w") as f:
                f.write(nginx_output)

    (site_path / ".env").write_text(f"""
SITE_NAME={name}
WEB_SERVER={webserver}
PORT={port}
WORDPRESS_DB_HOST=db
WORDPRESS_DB_USER=wordpress
WORDPRESS_DB_PASSWORD=wordpress
WORDPRESS_DB_NAME=wordpress
MYSQL_ROOT_PASSWORD=root
""".strip() + "\n")

    config = load_config()
    config[name] = {
        "path": str(site_path),
        "webserver": webserver,
        "port": port
    }
    save_config(config)

    typer.echo("[*] Añadiendo entrada al archivo hosts...")
    elevate_and_run([HOSTCTL_SCRIPT, "add-host", f"{name}.local"])

    typer.echo(f"[+] Instancia creada correctamente en el puerto {port}.")
    start(name, port)


@app.command()
def list():
    config = load_config()
    if not config:
        typer.echo("\n[!] No hay instancias registradas.")
        raise typer.Exit()

    typer.echo("\nInstancias registradas:")
    for name, data in config.items():
        typer.echo(f"- {name} (web: {data.get('webserver', 'apache')}, port: {data.get('port', 80)})")


@app.command()
def start(name: str, port: int = None):
    check_docker()
    config = load_config()
    if name not in config:
        typer.echo("\n[!] Instancia no encontrada.")
        raise typer.Exit(1)

    path = Path(config[name]['path'])
    typer.echo(f"[*] Iniciando instancia '{name}'...")
    subprocess.run(["docker", "compose", "up", "-d"], cwd=path)
    typer.echo("[+] Instancia iniciada.")
    if port:
        typer.echo(f"[*] Accede a tu sitio en http://localhost:{port}")


@app.command()
def stop(name: str):
    check_docker()
    config = load_config()
    if name not in config:
        typer.echo("\n[!] Instancia no encontrada.")
        raise typer.Exit(1)

    path = Path(config[name]['path'])
    typer.echo(f"[*] Deteniendo instancia '{name}'...")
    subprocess.run(["docker", "compose", "down"], cwd=path)
    typer.echo("[+] Instancia detenida.")


@app.command()
def delete(name: str):
    check_docker()
    config = load_config()
    if name not in config:
        typer.echo("\n[!] Instancia no encontrada.")
        raise typer.Exit(1)

    path = Path(config[name]['path'])
    typer.confirm("¿Estás seguro de eliminar esta instancia COMPLETAMENTE (contenedor, volúmenes, red, archivos, hosts)?", abort=True)

    typer.echo("[*] Eliminando contenedores, volúmenes y red...")
    subprocess.run(["docker", "compose", "down", "-v"], cwd=path)

    typer.echo("[*] Eliminando entrada en archivo hosts...")
    elevate_and_run([HOSTCTL_SCRIPT, "remove-host", f"{name}.local"])

    typer.echo("[*] Borrando archivos de la instancia...")
    elevate_and_run([HOSTCTL_SCRIPT, "rm-path", str(path)])

    del config[name]
    save_config(config)

    typer.echo("[+] Instancia eliminada completamente.")


@app.command()
def open(name: str):
    config = load_config()
    if name not in config:
        typer.echo("[!] Instancia no encontrada.")
        raise typer.Exit(1)
    port = config[name].get("port", 80)
    url = f"http://localhost:{port}"
    webbrowser.open(url)
    typer.echo(f"[*] Abriendo {url}")


if __name__ == "__main__":
    app()
