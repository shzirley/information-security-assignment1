"""Render entry point: retain external keys/data, migrate, then start one API worker."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    from kyc.cloud import configure_cloud_environment
    from kyc.db import database
    from kyc.migrate import migrate

    settings, _ = configure_cloud_environment()
    port = int(os.getenv('PORT', '10000'))
    if not 1 <= port <= 65535:
        raise RuntimeError('PORT must be between 1 and 65535.')
    engine = database(settings.database_url)
    try:
        migrate(engine, settings)
    finally:
        engine.dispose()
    print('BankKYC schema ready; starting API with external MySQL.', flush=True)
    os.execv(sys.executable, [sys.executable, '-m', 'uvicorn', 'app.server:app',
                            '--host', '0.0.0.0', '--port', str(port), '--workers', '1'])


if __name__ == '__main__':
    main()
