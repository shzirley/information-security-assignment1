from pathlib import Path
from alembic import command
from alembic.config import Config
from .provision import initialize_keys

def migrate(engine, settings):
    config = Config(str(Path(__file__).resolve().parents[1] / 'alembic.ini'))
    with engine.begin() as connection:
        config.attributes['connection'] = connection
        command.upgrade(config, 'head')
    initialize_keys(engine, settings)
