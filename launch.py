"""One-click launcher: start Streamlit if not already up, then open the browser."""
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

PORT = 8501
URL = f"http://localhost:{PORT}"
HERE = Path(__file__).parent


def port_is_open(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.4)
        try:
            return s.connect_ex((host, port)) == 0
        except OSError:
            return False


def main() -> None:
    if not port_is_open(PORT):
        # Streamlit not running — start it in a new console window
        creationflags = 0
        if sys.platform == "win32":
            creationflags = subprocess.CREATE_NEW_CONSOLE  # type: ignore[attr-defined]
        subprocess.Popen(
            [
                sys.executable, "-m", "streamlit", "run", "app.py",
                "--server.headless=true",
                "--server.port", str(PORT),
                "--browser.gatherUsageStats=false",
            ],
            cwd=str(HERE),
            creationflags=creationflags,
        )
        # Wait for the port to come up (max ~30s)
        for _ in range(60):
            time.sleep(0.5)
            if port_is_open(PORT):
                break

    webbrowser.open(URL)


if __name__ == "__main__":
    main()
