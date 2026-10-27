"""Initial BankKYC schema; isolated from legacy vault tables."""
from alembic import op
from kyc.db import metadata
revision = '0001_bankkyc'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    metadata.create_all(op.get_bind())
    op.get_bind().execute(metadata.tables['lab_lock'].insert().values(id=1, owner=None, expires_at=0))

def downgrade():
    metadata.drop_all(op.get_bind())
