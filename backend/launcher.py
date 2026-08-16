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
    """Check if a port is available. 返回 (是否可用, 错误码)。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        try:
            s.bind((host, port))
            return True, None
        except OSError as e:
            err = getattr(e, "winerror", None) or getattr(e, "errno", None)
            return False, err


def find_free_port():
    """在多个常用端口段中查找可用端口（自动跳过 Windows 系统保留端口）。

    部分 Windows 机器上 5000-5010 会被 Hyper-V/WSL 动态端口段保留（WinError 10013），
    此时继续在后续端口段中查找，保证程序仍可启动。
    """
    ranges = [
        (5000, 5010),
        (8000, 8010),
        (8080, 8090),
        (9000, 9010),
        (3000, 3010),
        (5173, 5183),
        (9500, 9600),
    ]
    os_reserved = []
    for lo, hi in ranges:
        for port in range(lo, hi + 1):
            free, err = is_port_free(port)
            if free:
                return port, os_reserved
            if err == 10013:  # 系统保留端口段（Hyper-V/WSL 动态端口）
                os_reserved.append(port)
    return None, os_reserved


def open_browser(port):
    time.sleep(1.5)
    webbrowser.open(f"http://127.0.0.1:{port}")


if __name__ == "__main__":
    static = get_static_dir()
    if not os.path.isdir(static):
        print(f"[WARN] 静态文件目录不存在: {static}")
        print("请先运行 build.bat 构建前端")

    port, os_reserved = find_free_port()
    if port is None:
        print("=" * 50)
        print("[错误] 未找到可用端口，程序无法启动。")
        if os_reserved:
            print(f"提示：{len(os_reserved)} 个端口被 Windows 系统保留"
                  f"（5000-5010 可能被 Hyper-V/WSL 动态端口段占用）。")
            print("可通过环境变量 TUTORING_PORT 手动指定一个空闲端口后重试。")
        else:
            print("请关闭占用端口的程序后再试，或通过环境变量 TUTORING_PORT 指定端口。")
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
        print(f"[提示] 默认端口 5000 不可用（被系统保留或被占用），已改用端口 {port}")
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
