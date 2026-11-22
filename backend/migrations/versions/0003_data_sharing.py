"""Add Assignment 2 public keys, requests and encrypted copies."""
from alembic import op
from kyc.db import user_public_keys, share_requests, share_items

revision = '0003_data_sharing'
down_revision = '0002_document_review'
branch_labels = None
depends_on = None

TABLES = (user_public_keys, share_requests, share_items)


def upgrade():
    # 0001 creates live metadata on a fresh install; upgrade older installs safely.
    for table in TABLES:
        table.create(op.get_bind(), checkfirst=True)


def downgrade():
    for table in reversed(TABLES):
        table.drop(op.get_bind(), checkfirst=True)
