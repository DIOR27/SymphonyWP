from jinja2 import Environment, FileSystemLoader
from pathlib import Path

from symphony.docker_utils import check_docker, generate_random_port

import builtins, os, time, json, webbrowser, platform, subprocess, threading, itertools
import typer, locale, gettext
import requests

BASE_DIR = Path(__file__).resolve().parent

def setup_i18n():
    lang = (locale.getlocale()[0] or "es").split("_")[0]
    localedir = str(BASE_DIR / "locales")
    try:
        t = gettext.translation("cli", localedir=localedir, languages=[lang])
        t.install()
        return t.gettext
    except FileNotFoundError:
        return lambda s: s


_ = setup_i18n()


lang = os.getenv("CLI_LANG") or (locale.getlocale()[0] or 'es').split('_')[0]

app = typer.Typer()

SITES_DIR = BASE_DIR / "sites"
TEMPLATES_DIR = BASE_DIR / "templates"
CONFIG_FILE = BASE_DIR / "config.json"
HOSTCTL_SCRIPT = str(BASE_DIR / "hostctl.py")

TEMPLATES_DIR.mkdir(exist_ok=True)
SITES_DIR.mkdir(exist_ok=True)


def elevate_and_run(args):
    if platform.system() == "Windows":
        subprocess.run(
            [
                "powershell",
                "-Command",
                f"Start-Process python -ArgumentList {','.join(repr(a) for a in args)} -Verb RunAs",
            ]
        )
    else:
        subprocess.run(["sudo", "python3"] + args)


def load_config():
    if not CONFIG_FILE.exists():
        return {}
    with builtins.open(CONFIG_FILE) as f:
        return json.load(f)


def save_config(data):
    with builtins.open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)


@app.command()
def create(
    name: str,
    webserver: str = typer.Option(
        "apache", help="Tipo de servidor web: apache o nginx"
    ),
):
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

    (body_size := "256M")

    (site_path / ".env").write_text(
        f"""
SITE_NAME={name}
WEB_SERVER={webserver}
PORT={port}
WORDPRESS_DB_HOST=db
WORDPRESS_DB_USER=wordpress
WORDPRESS_DB_PASSWORD=wordpress
WORDPRESS_DB_NAME=wordpress
MYSQL_ROOT_PASSWORD=root
CLIENT_MAX_BODY_SIZE={body_size}
""".strip()
        + "\n"
    )
    (site_path / "php.ini").write_text(
        """
upload_max_filesize = 256M
post_max_size = 256M
memory_limit = 512M
""".strip()
        + "\n"
    )

    config = load_config()
    config[name] = {"path": str(site_path), "webserver": webserver, "port": port}
    save_config(config)

    typer.echo(_("[*] Añadiendo entrada al archivo hosts..."))
    elevate_and_run([HOSTCTL_SCRIPT, "add-host", f"{name}.local"])

    typer.echo(f"[+] Instancia creada correctamente en el puerto {port}.")
    start(name, port)


@app.command()
def list():
    config = load_config()
    if not config:
        typer.echo(_("\n[!] No hay instancias registradas."))
        raise typer.Exit()

    typer.echo(_("\nInstancias registradas:"))
    for name, data in config.items():
        typer.echo(
            f"- {name} (web: {data.get('webserver', 'apache')}, port: {data.get('port', 80)})"
        )


@app.command()
def start(name: str, port: int = None):
    check_docker()
    config = load_config()
    if name not in config:
        typer.echo(_("\n[!] Instancia no encontrada."))
        raise typer.Exit(1)

    path = Path(config[name]["path"])
    port = port or config[name].get("port", 80)

    typer.echo(f"[*] Iniciando instancia '{name}'...")
    subprocess.run(["docker", "compose", "up", "-d"], cwd=path)

    wait_for_site(port)

    typer.echo(f"[*] Accede a tu sitio en http://localhost:{port}")


@app.command()
def stop(name: str):
    check_docker()
    config = load_config()
    if name not in config:
        typer.echo(_("\n[!] Instancia no encontrada."))
        raise typer.Exit(1)

    path = Path(config[name]["path"])
    typer.echo(f"[*] Deteniendo instancia '{name}'...")
    subprocess.run(["docker", "compose", "down"], cwd=path)
    typer.echo(_("[+] Instancia detenida."))


@app.command()
def delete(
    name: str,
    yes: bool = typer.Option(
        False, "--yes", "-y", help="Omitir confirmación interactiva"
    ),
):
    check_docker()
    config = load_config()
    if name not in config:
        typer.echo(_("\n[!] Instancia no encontrada."))
        raise typer.Exit(1)

    path = Path(config[name]["path"])
    if not yes and not localized_confirm(
        _("¿Estás seguro de eliminar esta instancia COMPLETAMENTE (contenedor, volúmenes, red, archivos, hosts)?")
    ):
        typer.echo(_("[*] Operación cancelada."))
        raise typer.Exit()

    typer.echo(_("[*] Eliminando contenedores, volúmenes y red..."))
    subprocess.run(["docker", "compose", "down", "-v"], cwd=path)

    typer.echo(_("[*] Eliminando entrada en archivo hosts..."))
    elevate_and_run([HOSTCTL_SCRIPT, "remove-host", f"{name}.local"])

    typer.echo(_("[*] Borrando archivos de la instancia..."))
    elevate_and_run([HOSTCTL_SCRIPT, "rm-path", str(path)])

    del config[name]
    save_config(config)

    typer.echo(_("[+] Instancia eliminada completamente."))


@app.command()
def open(name: str):
    config = load_config()
    if name not in config:
        typer.echo(_("[!] Instancia no encontrada."))
        raise typer.Exit(1)
    port = config[name].get("port", 80)
    url = f"http://localhost:{port}"
    webbrowser.open(url)
    typer.echo(f"[*] Abriendo {url}")


@app.command()
@app.command()
def configure(
    name: str,
    editor: str = typer.Option(
        None, help="Editor para abrir los archivos (nano, code, etc.)"
    ),
    upload_max_filesize: str = typer.Option(
        None, help="Tamaño máximo de archivos (ej: 256M)"
    ),
    post_max_size: str = typer.Option(None, help="Tamaño máximo de POST (ej: 256M)"),
    max_execution_time: str = typer.Option(
        None, help="Tiempo máximo de ejecución (segundos)"
    ),
):
    config = load_config()
    if name not in config:
        typer.echo(f"[!] Instancia '{name}' no encontrada.")
        raise typer.Exit(1)

    site_path = Path(config[name]["path"])
    php_ini_path = site_path / "php.ini"

    # Si se pasó alguna opción de configuración, editar php.ini
    if any([upload_max_filesize, post_max_size, max_execution_time]):
        typer.echo("[*] Modificando directivas de PHP...")

        ini_lines = []
        if php_ini_path.exists():
            with php_ini_path.open() as f:
                ini_lines = f.readlines()

        def set_or_update(key: str, value: str):
            updated = False
            for i, line in enumerate(ini_lines):
                if line.strip().startswith(f"{key}"):
                    ini_lines[i] = f"{key} = {value}\n"
                    updated = True
                    break
            if not updated:
                ini_lines.append(f"{key} = {value}\n")

        if upload_max_filesize:
            set_or_update("upload_max_filesize", upload_max_filesize)
        if post_max_size:
            set_or_update("post_max_size", post_max_size)
        if max_execution_time:
            set_or_update("max_execution_time", max_execution_time)

        with php_ini_path.open("w") as f:
            f.writelines(ini_lines)

        typer.echo(_("[+] Configuración actualizada."))
        return

    # Si no hay claves, abre archivos con editor
    files_to_edit = [site_path / ".env", php_ini_path]
    nginx_path = site_path / "nginx" / "conf.d" / "default.conf"
    apache_path = site_path / "apache" / "apache2.conf"
    if nginx_path.exists():
        files_to_edit.append(nginx_path)
    if apache_path.exists():
        files_to_edit.append(apache_path)

    typer.echo("[*] Archivos a configurar:")
    for i, file in enumerate(files_to_edit):
        typer.echo(f"  {i+1}. {file}")
        if not file.exists():
            typer.echo(_(f"    [!] No existe."))
            continue

        if editor:
            subprocess.run([editor, str(file)])
        else:
            if platform.system() == "Windows":
                os.startfile(file)
            elif platform.system() == "Darwin":
                subprocess.run(["open", str(file)])
            else:
                subprocess.run(["xdg-open", str(file)])


def wait_for_site(port: int, timeout: int = 30):
    url = f"http://localhost:{port}"
    spinner = itertools.cycle(["⠋", "⠙", "⠸", "⠴", "⠦", "⠇"])
    done = False

    def spin():
        while not done:
            typer.echo(
                f"\r[*] Esperando que el sitio en {url} esté disponible... {next(spinner)}",
                nl=False,
            )
            time.sleep(0.2)

    thread = threading.Thread(target=spin)
    thread.start()

    for _ in range(timeout):
        try:
            r = requests.get(url, timeout=2)
            if r.status_code in [
                200,
                302,
                403,
            ]:  # WordPress puede responder 403 cuando aún no está instalado
                done = True
                thread.join()
                typer.echo(f"\r[+] Sitio disponible en {url}                  ")
                return
        except requests.exceptions.RequestException:
            pass
        time.sleep(1)

    done = True
    thread.join()
    typer.echo(f"\r[!] Tiempo agotado. Intenta abrir manualmente: {url}")


def localized_confirm(message: str) -> bool:
    import locale

    lang = (locale.getlocale()[0] or "").lower()

    if lang.startswith("es"):
        yes_key = "s"
        no_key = "n"
    else:
        yes_key = "y"
        no_key = "n"

    prompt = f"{message} [{yes_key.lower()}/{no_key.upper()}]: "
    while True:
        response = input(prompt).strip().lower()
        if response == "":
            return False  # default is No
        elif response == yes_key:
            return True
        elif response == no_key:
            return False
        else:
            typer.echo(
                f"Por favor, ingresa '{yes_key}' o '{no_key}' (Enter = {no_key.upper()})."
            )


if __name__ == "__main__":
    app()
