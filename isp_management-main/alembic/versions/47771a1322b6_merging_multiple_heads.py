"""Merging multiple heads

Revision ID: 47771a1322b6
Revises: 20230601_tariff_enforcement, 7961efb2e4db, add_elasticsearch_synced_field, ai_chatbot_integration
Create Date: 2025-03-15 13:50:27.139534

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '47771a1322b6'
down_revision: Union[str, None] = ('20230601_tariff_enforcement', '7961efb2e4db', 'add_elasticsearch_synced_field', 'ai_chatbot_integration')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
