"""Add document subtype, encrypted review checklist and analysis references."""
from alembic import op
import sqlalchemy as sa
from kyc.db import document_analyses, evidence_types, review_records

revision = '0002_document_review'
down_revision = '0001_bankkyc'
branch_labels = None
depends_on = None

TABLES = (evidence_types, review_records, document_analyses)


def upgrade():
    available = {column['name'] for column in sa.inspect(op.get_bind()).get_columns('security_events')}
    for name, size in (('application_id', 36), ('evidence_id', 36), ('outcome', 16)):
        if name not in available:
            op.add_column('security_events', sa.Column(name, sa.String(size)))
    # 0001 uses live metadata, so a clean install may already have these tables.
    for table in TABLES:
        table.create(op.get_bind(), checkfirst=True)


def downgrade():
    for table in reversed(TABLES):
        table.drop(op.get_bind(), checkfirst=True)
    with op.batch_alter_table('security_events') as batch:
        for name in ('outcome', 'evidence_id', 'application_id'):
            batch.drop_column(name)
