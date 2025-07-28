# SymphonyWP

A cross-platform CLI to easily create, manage, and launch multiple isolated WordPress instances using Docker and a reverse proxy — all with a single command.

---

## 🚀 Features

- Isolated environments for each WordPress site
- Support for Apache or Nginx web server
- Automatic configuration of Docker, volumes, and virtual hosts
- Friendly CLI with localization (Spanish by default)
- Runs on Linux, macOS, and Windows (via PowerShell)
- Multilingual-ready

---

## 🔧 Prerequisites

- [Python 3.8+](https://www.python.org/)
- [Docker](https://www.docker.com/get-started)
- Internet connection to install dependencies via `pipx`

---

## 📦 Installation

### 🐧 Linux / macOS

```bash
curl -sSL https://raw.githubusercontent.com/your-username/symphonywp/main/install.sh | bash
```

You may need to restart your terminal or run `source ~/.bashrc` after installation.

---

### 🪟 Windows (PowerShell)

Run this from PowerShell as administrator:

```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
irm https://raw.githubusercontent.com/your-username/symphonywp/main/install.ps1 | iex
```

This will install `pipx` (if needed), set your path, and install `symphony`.

---

## 📘 Usage

```bash
symphony --help
```

### Examples

```bash
symphony create demo1 --webserver apache
symphony list
symphony open demo1
symphony delete demo1
```

---

## 🌐 Localization

This CLI supports multilingual messages via gettext. By default, the interface is in Spanish. You can change the language by setting the `CLI_LANG` environment variable:

```bash
export CLI_LANG=en  # or es, fr, etc.
```

---

## 🧪 Development

To run the CLI locally for testing:

```bash
pipx install .
symphony --help
```

To uninstall:

```bash
pipx uninstall symphony
```

---

## 📄 License

MIT License © 2025 - SymphonyWP Contributors