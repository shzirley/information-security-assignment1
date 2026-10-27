from alembic import context
from kyc.config import Settings
from kyc.db import metadata, database

def run(connection):
    context.configure(connection=connection, target_metadata=metadata, render_as_batch=connection.dialect.name == 'sqlite')
    with context.begin_transaction():
        context.run_migrations()

provided = context.config.attributes.get('connection')
if provided is not None:
    run(provided)
else:
    engine = database(Settings.from_env().database_url)
    with engine.connect() as connection:
        run(connection)
    engine.dispose()
