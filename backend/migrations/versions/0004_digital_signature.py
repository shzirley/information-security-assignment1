"""Add Assignment 3 signing keys, CA, sessions and signed document references."""
from alembic import op
from kyc.db import (user_signing_keys, signing_key_challenges, pki_authority,
                    signature_sessions, document_signatures)

revision = '0004_digital_signature'
down_revision = '0003_data_sharing'
branch_labels = None
depends_on = None

TABLES = (user_signing_keys, signing_key_challenges, pki_authority,
          signature_sessions, document_signatures)


def upgrade():
    # 0001 uses live metadata on clean installs, so tables can exist already.
    for table in TABLES:
        table.create(op.get_bind(), checkfirst=True)


def downgrade():
    for table in reversed(TABLES):
        table.drop(op.get_bind(), checkfirst=True)
