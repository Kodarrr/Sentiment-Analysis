"""add fine grained sentiment columns

Revision ID: 3a1c5d9e7b2f
Revises: edff404f748a
Create Date: 2026-10-16 11:26:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3a1c5d9e7b2f'
down_revision: Union[str, None] = 'edff404f748a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('feedback', sa.Column('sentiment_polarity', sa.String(length=20), nullable=True))
    op.add_column('feedback', sa.Column('confidence', sa.Float(), nullable=True))
    op.add_column('feedback', sa.Column('probabilities', sa.JSON(), nullable=True))
    op.add_column('feedback', sa.Column('model_id', sa.String(length=255), nullable=True))
    op.add_column('feedback', sa.Column('model_revision', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('feedback', 'model_revision')
    op.drop_column('feedback', 'model_id')
    op.drop_column('feedback', 'probabilities')
    op.drop_column('feedback', 'confidence')
    op.drop_column('feedback', 'sentiment_polarity')

