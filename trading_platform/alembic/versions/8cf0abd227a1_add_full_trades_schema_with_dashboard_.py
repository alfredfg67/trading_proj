"""Add full trades schema with dashboard columns

Revision ID: 8cf0abd227a1
Revises: 
Create Date: 2026-08-05 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '8cf0abd227a1'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create orders table
    op.create_table('orders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('side', sa.String(), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('price', sa.Float(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_orders_id', 'orders', ['id'], unique=False)

    # Create trades table with all columns
    op.create_table('trades',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticket_id', sa.Integer(), nullable=True),
        sa.Column('order_id', sa.Integer(), nullable=True),
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('instrument_type', sa.String(), nullable=False),
        sa.Column('direction', sa.String(), nullable=False),
        sa.Column('lot_size', sa.Float(), nullable=False),
        sa.Column('entry_time', sa.DateTime(), nullable=False),
        sa.Column('exit_time', sa.DateTime(), nullable=False),
        sa.Column('entry_price', sa.Float(), nullable=False),
        sa.Column('exit_price', sa.Float(), nullable=False),
        sa.Column('stop_loss', sa.Float(), nullable=True),
        sa.Column('take_profit', sa.Float(), nullable=True),
        sa.Column('profit', sa.Float(), nullable=False),
        sa.Column('commission', sa.Float(), nullable=True),
        sa.Column('swap', sa.Float(), nullable=True),
        sa.Column('slippage', sa.Float(), nullable=True),
        sa.Column('session', sa.String(), nullable=True),
        sa.Column('strategy_tag', sa.String(), nullable=True),
        sa.Column('account_balance_after', sa.Float(), nullable=True),
        sa.Column('backtest_expected_pnl', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], name='fk_trades_order_id'),
    )
    # Indexes
    op.create_index('ix_trades_id', 'trades', ['id'], unique=False)
    op.create_index('ix_trades_ticket_id', 'trades', ['ticket_id'], unique=True)
    op.create_index('idx_trades_symbol_entry_time', 'trades', ['symbol', 'entry_time'])
    op.create_index('idx_trades_instrument_type', 'trades', ['instrument_type'])
    op.create_index('idx_trades_session', 'trades', ['session'])
    op.create_index('idx_trades_strategy_tag', 'trades', ['strategy_tag'])

def downgrade():
    # Drop indexes
    op.drop_index('idx_trades_strategy_tag', table_name='trades')
    op.drop_index('idx_trades_session', table_name='trades')
    op.drop_index('idx_trades_instrument_type', table_name='trades')
    op.drop_index('idx_trades_symbol_entry_time', table_name='trades')
    op.drop_index('ix_trades_ticket_id', table_name='trades')
    op.drop_index('ix_trades_id', table_name='trades')
    # Drop tables
    op.drop_table('trades')
    op.drop_table('orders')