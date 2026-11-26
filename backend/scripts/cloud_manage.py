"""Run operator CLI against cloud MySQL without modifying backend/.env."""
import argparse
import os
import subprocess
import sys
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', type=Path, required=True)
    parser.add_argument('command', choices=['migrate', 'create-user', 'disable-user'])
    parser.add_argument('arguments', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    from kyc.cloud import REQUIRED, configure_cloud_environment
    values = dotenv_values(args.env_file)
    missing = [name for name in (*REQUIRED, 'APP_ENV', 'COOKIE_SECURE') if not values.get(name)]
    if missing:
        parser.error('Cloud env file is incomplete: ' + ', '.join(missing))
    for name in (*REQUIRED, 'APP_ENV', 'COOKIE_SECURE'):
        os.environ[name] = values[name]
    _, ca_path = configure_cloud_environment()
    try:
        return subprocess.run([sys.executable, str(ROOT / 'manage.py'), args.command, *args.arguments], cwd=ROOT).returncode
    finally:
        ca_path.unlink(missing_ok=True)


if __name__ == '__main__':
    sys.exit(main())
