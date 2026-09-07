"""add_phase_4_rule_versioning_period_closure_notifications

Revision ID: 7432e428334b
Revises: 202281ad12d6
Create Date: 2026-09-04 13:54:33.971525

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7432e428334b'
down_revision: Union[str, Sequence[str], None] = '202281ad12d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Commission tiers versioning
    op.add_column('commission_tiers', sa.Column('effective_from', sa.Date(), nullable=False, server_default='2026-01-01'))
    op.add_column('commission_tiers', sa.Column('effective_to', sa.Date(), nullable=True))
    op.add_column('commission_tiers', sa.Column('created_by_user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True))

    # 2. Role commission tiers versioning
    op.add_column('role_commission_tiers', sa.Column('effective_from', sa.Date(), nullable=False, server_default='2026-01-01'))
    op.add_column('role_commission_tiers', sa.Column('effective_to', sa.Date(), nullable=True))
    op.add_column('role_commission_tiers', sa.Column('created_by_user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True))

    # 3. Transaction categories versioning
    op.add_column('transaction_categories', sa.Column('effective_from', sa.Date(), nullable=False, server_default='2026-01-01'))
    op.add_column('transaction_categories', sa.Column('effective_to', sa.Date(), nullable=True))
    op.add_column('transaction_categories', sa.Column('created_by_user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True))

    # 4. Rule Change Logs Table
    op.create_table(
        'rule_change_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('branch_id', sa.Integer(), sa.ForeignKey('branches.id'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('rule_type', sa.String(length=50), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('effective_from', sa.Date(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('old_values', sa.JSON(), nullable=True),
        sa.Column('new_values', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_rule_change_logs_id'), 'rule_change_logs', ['id'], unique=False)
    op.create_index(op.f('ix_rule_change_logs_branch_id'), 'rule_change_logs', ['branch_id'], unique=False)

    # 5. Period Closures Table
    op.create_table(
        'period_closures',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('branch_id', sa.Integer(), sa.ForeignKey('branches.id'), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('month', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='CLOSED'),
        sa.Column('closed_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('closed_by_user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('reconciliation_snapshot', sa.JSON(), nullable=True),
        sa.Column('bonus_snapshot', sa.JSON(), nullable=True),
        sa.Column('reopened_at', sa.DateTime(), nullable=True),
        sa.Column('reopened_by_user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('reopen_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_period_closures_id'), 'period_closures', ['id'], unique=False)
    op.create_index(op.f('ix_period_closures_branch_id'), 'period_closures', ['branch_id'], unique=False)

    # 6. Notifications Table
    op.create_table(
        'notifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('branch_id', sa.Integer(), sa.ForeignKey('branches.id'), nullable=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('payload', sa.JSON(), nullable=True),
        sa.Column('channel', sa.String(length=30), nullable=False, server_default='in-app'),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notifications_id'), 'notifications', ['id'], unique=False)
    op.create_index(op.f('ix_notifications_branch_id'), 'notifications', ['branch_id'], unique=False)
    op.create_index(op.f('ix_notifications_user_id'), 'notifications', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('notifications')
    op.drop_table('period_closures')
    op.drop_table('rule_change_logs')

    op.drop_column('transaction_categories', 'created_by_user_id')
    op.drop_column('transaction_categories', 'effective_to')
    op.drop_column('transaction_categories', 'effective_from')

    op.drop_column('role_commission_tiers', 'created_by_user_id')
    op.drop_column('role_commission_tiers', 'effective_to')
    op.drop_column('role_commission_tiers', 'effective_from')

    op.drop_column('commission_tiers', 'created_by_user_id')
    op.drop_column('commission_tiers', 'effective_to')
    op.drop_column('commission_tiers', 'effective_from')
