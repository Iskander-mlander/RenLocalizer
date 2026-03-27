# 📥 Installation Guide

RenLocalizer is designed to be flexible. You can run it as a standalone executable on Windows or from the source code on any platform (macOS, Linux, Windows).

---

## 🪟 Windows (Standalone)
The easiest way to use RenLocalizer on Windows:

1.  Navigate to the [Releases](https://github.com/Lord0fTurk/RenLocalizer/releases) page.
2.  Download the latest `RenLocalizer_vX.X.X_Windows.zip`.
3.  **Extract** the ZIP file to a folder of your choice.
4.  Run `RenLocalizer.exe` to start the GUI.

> 🚀 **v2.7.4 Update:** RenLocalizer now defaults to **System Mode** (AppData). If you specifically want a portable experience (e.g., on a USB stick), toggle **Portable Mode** in Settings to move all your data next to the executable.

---

## 🐧 Linux (Pre-built Binary)
Pre-built AppImage and portable tar.gz are available from the [Releases](https://github.com/Lord0fTurk/RenLocalizer/releases) page.

### AppImage
```bash
chmod +x RenLocalizer-Linux-x64.AppImage
./RenLocalizer-Linux-x64.AppImage
```

### Portable tar.gz
```bash
tar -xzf RenLocalizer-Linux-x64.tar.gz
cd RenLocalizer
chmod +x RenLocalizer.sh
./RenLocalizer.sh
```

> 💡 **Auto-recovery:** If OpenGL/GLX hardware acceleration is unavailable (common on immutable distros like Bazzite, Fedora Atomic, or VMs without GPU passthrough), the launcher automatically retries with software rendering.

### 🔧 Linux Troubleshooting

**"Could not initialize GLX" / App crashes immediately:**
The bundled Qt libraries require OpenGL/GLX support. If your system cannot provide hardware-accelerated GLX (e.g. missing GPU drivers, container environments, Wayland-only sessions), force software rendering:

```bash
QT_QUICK_BACKEND=software ./RenLocalizer-Linux-x64.AppImage
# or for the tar.gz version:
QT_QUICK_BACKEND=software ./RenLocalizer.sh
```

> 📝 **Note:** As of v2.7.6, this fallback happens automatically. You should only need the manual override if auto-detection does not work for your setup.

**Missing emoji icons:**
Install a color emoji font:
```bash
# Fedora/RHEL
sudo dnf install google-noto-color-emoji-fonts
# Ubuntu/Debian
sudo apt install fonts-noto-color-emoji
```

---

## 🍎 macOS & 🐧 Linux (from Source)
Since RenLocalizer is built with Python 3, it works natively on Unix-based systems.

### 📋 Prerequisites
*   **Python 3.10** or higher.
*   **pip** (Python package manager).

### 🛠️ Step-by-Step Setup
1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/Lord0fTurk/RenLocalizer.git
    cd RenLocalizer
    ```

2.  **Create a Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # macOS/Linux
    # venv\Scripts\activate   # Windows
    ```

3.  **Install Dependencies:**
    ```bash
    # Flexible source install (CI-smoke-tested across PyQt6 6.6-6.10 on Linux)
    pip install -r requirements.txt

    # Optional: match the exact packaged-build Qt stack
    # pip install -c constraints-release.txt -r requirements.txt
    ```

4.  **Launch the Application:**
    *   **GUI:** `python run.py`
    *   **CLI:** `python run_cli.py`

---

## 🚀 Convenience Scripts
We provide pre-made scripts to handle the environment setup automatically:

*   **`RenLocalizer.sh`**: Launches the bundled portable build when present, or bootstraps a local VENV and starts the GUI in a source checkout.
*   **`RenLocalizerCLI.sh`**: Sets up the VENV and launches the CLI.

> 💡 **Note:** Make sure to grant execution permissions on Linux/macOS:
> `chmod +x RenLocalizer.sh`

---

## 📦 Core Dependencies
The tool relies on these main libraries:
*   **UI:** `PyQt6` + QML/Qt Quick
*   **AI:** `openai`, `google-genai`
*   **Extraction:** `unrpa`
*   **Engines:** `requests`, `httpx`, `beautifulsoup4`

### PyQt6 Compatibility Policy
*   **Source installs:** use the tested compatibility range from `requirements.txt`.
*   **Official packaged builds / reproducible local builds:** use `constraints-release.txt` together with `requirements.txt`.
*   **CI coverage:** Linux source installs are validated with a Qt startup smoke test across the PyQt6 `6.6.x` to `6.10.x` line.
