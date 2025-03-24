"""merge ai_chatbot_integration and 7961efb2e4db

Revision ID: d19c3d9506bc
Revises: 7961efb2e4db, ai_chatbot_integration
Create Date: 2025-03-16 12:05:30.142615

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd19c3d9506bc'
down_revision: Union[str, None] = ('7961efb2e4db', 'ai_chatbot_integration')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
