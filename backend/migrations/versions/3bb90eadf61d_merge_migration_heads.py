"""merge migration heads

Revision ID: 3bb90eadf61d
Revises: 20260517190000, 20260518001000, a620cabab08e
Create Date: 2026-05-18 13:36:50.152011

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3bb90eadf61d'
down_revision: Union[str, Sequence[str], None] = ('20260517190000', '20260518001000', 'a620cabab08e')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
