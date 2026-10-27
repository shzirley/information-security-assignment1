"""One-command local setup and startup; service failures are shown, never hidden."""
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.request
import venv
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND, FRONTEND = ROOT / 'backend', ROOT / 'frontend'

def run(command, cwd):
    subprocess.run([str(x) for x in command], cwd=cwd, check=True)

def main():
    if sys.version_info < (3, 11):
        raise RuntimeError('Python 3.11+ is required.')
    npm = shutil.which('npm.cmd' if os.name == 'nt' else 'npm')
    if not npm:
        raise RuntimeError('Install Node.js 22+ including npm, then reopen this terminal.')
    node = shutil.which('node')
    major = int(subprocess.check_output([node, '-p', 'process.versions.node.split(".")[0]'], text=True).strip())
    if major < 22:
        raise RuntimeError('Node.js 22+ is required.')
    if not shutil.which('ffprobe') and not os.getenv('FFPROBE_PATH'):
        print('Note: MP4 upload requires FFmpeg (ffprobe). Configure backend/.env if using a custom path.', flush=True)
    for port in (8000, 3000):
        with socket.socket() as probe:
            if probe.connect_ex(('127.0.0.1', port)) == 0:
                raise RuntimeError(f'Port {port} is in use. Close the old server and run again.')
    environment = BACKEND / '.venv'
    python = environment / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if not python.exists():
        print('Creating Python environment...', flush=True)
        venv.create(environment, with_pip=True)
    stamp = environment / '.veltrix-requirements'
    requirements = (BACKEND / 'requirements.txt').read_bytes() + b'\n' + (BACKEND / 'constraints-tested.txt').read_bytes()
    if not stamp.exists() or stamp.read_bytes() != requirements:
        run([python, '-m', 'pip', 'install', '-r', 'requirements.txt'], BACKEND)
        stamp.write_bytes(requirements)
    run([python, 'setup_env.py', '--live'], BACKEND)
    run([python, 'manage.py', 'migrate'], BACKEND)
    run([python, 'manage.py', 'demo-users'], BACKEND)
    lock = (FRONTEND / 'package-lock.json').read_bytes()
    npm_stamp = FRONTEND / 'node_modules' / '.veltrix-lock'
    if not npm_stamp.exists() or npm_stamp.read_bytes() != lock:
        run([npm, 'ci', '--no-audit', '--no-fund'], FRONTEND)
        npm_stamp.write_bytes(lock)
    children = []
    def stop(*_):
        for child in children:
            if child.poll() is None:
                if os.name == 'nt':
                    subprocess.run(['taskkill', '/PID', str(child.pid), '/T', '/F'], capture_output=True)
                else:
                    try:
                        os.killpg(child.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
    try:
        options = {'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == 'nt' else {'start_new_session': True}
        children.append(subprocess.Popen([str(python), '-m', 'uvicorn', 'app.server:app', '--host', '127.0.0.1', '--port', '8000'], cwd=BACKEND, **options))
        for _ in range(60):
            if children[0].poll() is not None:
                raise RuntimeError('Backend could not start; see the error above.')
            try:
                with urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=1) as response:
                    if response.status == 200:
                        break
            except Exception:
                time.sleep(0.5)
        else:
            raise RuntimeError('Backend startup timed out.')
        children.append(subprocess.Popen([npm, 'run', 'dev'], cwd=FRONTEND, **options))
        print('\nOpen http://127.0.0.1:3000 — data is saved in backend/data/bankkyc.db. Ctrl+C stops both servers.', flush=True)
        for _ in range(120):
            if any(child.poll() is not None for child in children):
                raise RuntimeError('A server stopped unexpectedly; see the error above.')
            try:
                with urllib.request.urlopen('http://127.0.0.1:3000', timeout=1):
                    break
            except Exception:
                time.sleep(0.5)
        webbrowser.open('http://127.0.0.1:3000')
        while all(child.poll() is None for child in children):
            time.sleep(0.5)
    finally:
        stop()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\nServers stopped. Data remains saved.')
    except Exception as exc:
        print(f'\nStartup failed: {exc}', file=sys.stderr)
        sys.exit(1)
