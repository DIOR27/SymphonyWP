import sys
import os
import shutil
import platform


def get_hosts_path():
    if platform.system() == "Windows":
        return os.path.join(os.environ['SystemRoot'], 'System32', 'drivers', 'etc', 'hosts')
    return "/etc/hosts"


def add_entry(domain):
    line = f"127.0.0.1 {domain}\n"
    hosts = get_hosts_path()
    with open(hosts, "r") as f:
        lines = f.readlines()
    if any(domain in l for l in lines):
        return
    with open(hosts, "a") as f:
        f.write(line)


def remove_entry(domain):
    hosts = get_hosts_path()
    with open(hosts, "r") as f:
        lines = f.readlines()
    with open(hosts, "w") as f:
        for l in lines:
            if domain not in l:
                f.write(l)


def delete_path(path):
    shutil.rmtree(path, ignore_errors=True)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Uso: hostctl.py [add-host|remove-host|rm-path] <valor>")
        sys.exit(1)

    action = sys.argv[1]
    target = sys.argv[2]

    if action == "add-host":
        add_entry(target)
    elif action == "remove-host":
        remove_entry(target)
    elif action == "rm-path":
        delete_path(target)
    else:
        print("Acción no reconocida.")
