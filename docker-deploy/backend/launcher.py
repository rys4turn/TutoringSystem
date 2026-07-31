"""
Launcher entry point - starts uvicorn and opens browser (local) or serves headless (Docker/NAS).
Used both in development and as the PyInstaller entry point.
"""
import os
import sys
import time
import socket
import threading
import webbrowser
import uvicorn

# Ensure UTF-8 output for Chinese characters in Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

def get_static_dir():
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, "static")
    here = os.path.dirname(os.path.abspath(__file__))
    # Prefer a "static" dir next to launcher.py (Docker layout)
    candidate = os.path.join(here, "static")
    if os.path.isdir(candidate):
        return candidate
    return os.path.join(here, "static")


def is_port_free(port, host="127.0.0.1"):
    """Check if a port is available."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False


def find_free_port(start=5000, end=5010):
    """Find the first free port in range."""
    for port in range(start, end + 1):
        if is_port_free(port):
            return port
    return None


def open_browser(port):
    time.sleep(1.5)
    webbrowser.open(f"http://127.0.0.1:{port}")


if __name__ == "__main__":
    static = get_static_dir()
    if not os.path.isdir(static):
        print(f"[WARN] 静态文件目录不存在: {static}")
        print("请先运行 build.bat 构建前端")

    port = find_free_port()
    if port is None:
        print("=" * 50)
        print("[错误] 端口 5000-5010 全部被占用！")
        print("请关闭正在运行的程序后再试。")
        print("=" * 50)
        input("按回车键退出...")
        sys.exit(1)

    # Host configuration: env override for NAS/Docker, default to all interfaces
    host = os.environ.get("TUTORING_HOST", "0.0.0.0")
    port_env = os.environ.get("TUTORING_PORT", "")
    if port_env:
        port = int(port_env)

    # Database path
    db_path = os.environ.get("TUTORING_DB") or (
        os.path.join(os.path.dirname(sys.executable), "tutoring.db")
        if getattr(sys, "frozen", False) else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tutoring.db"))

    print("=" * 50)
    print("  补习班教务管理系统")
    print("=" * 50)
    if port_env and port != 5000:
        print(f"[提示] 使用指定端口 {port}")
    elif port != 5000:
        print(f"[提示] 默认端口 5000 已被占用，使用端口 {port}")
    print(f"监听地址: {host}:{port}")
    print(f"数据库: {db_path}")

    # Skip browser auto-open in container / server mode
    in_docker = os.path.exists("/.dockerenv") or os.environ.get("DOCKER_ENV")
    if not in_docker:
        threading.Thread(target=open_browser, args=(port,), daemon=True).start()
        print(f"浏览器将自动打开 http://127.0.0.1:{port}")
    print("关闭此窗口即可停止服务")
    print("=" * 50)

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        log_level="info",
    )