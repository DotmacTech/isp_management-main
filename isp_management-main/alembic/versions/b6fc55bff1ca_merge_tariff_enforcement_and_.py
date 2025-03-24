"""merge d19c3d9506bc

Revision ID: b6fc55bff1ca
Revises: d19c3d9506bc
Create Date: 2025-03-16 12:15:29.284990

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b6fc55bff1ca'
down_revision: Union[str, None] = 'd19c3d9506bc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
