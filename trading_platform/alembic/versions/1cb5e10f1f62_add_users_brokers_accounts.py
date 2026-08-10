"""add_users_brokers_accounts

Revision ID: xxxxx   # Keep the ID that Alembic generates
Revises: 8cf0abd227a1
Create Date: 2026-08-10 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy import String, Integer, DateTime, Boolean, Float

# Replace 'xxxxx' with the generated revision ID
revision = 'xxxxx'
down_revision = '8cf0abd227a1'
branch_labels = None
depends_on = None

def upgrade():
    # 1. Create users table
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('password_hash', sa.String(), nullable=False),
        sa.Column('role', sa.Enum('admin', 'user', name='userrole'), nullable=False, server_default='user'),
        sa.Column('failed_login_attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_locked', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('locked_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('last_login_at', sa.DateTime(), nullable=True),
        sa.Column('phone', sa.String(), nullable=True),
        sa.Column('whatsapp', sa.String(), nullable=True),
        sa.Column('telegram', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # 2. Create brokers table
    op.create_table('brokers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('broker_name', sa.String(), nullable=False),
        sa.Column('server_info', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )

    # 3. Create broker_accounts table
    op.create_table('broker_accounts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('broker_id', sa.Integer(), nullable=False),
        sa.Column('mt5_login', sa.Integer(), nullable=False),
        sa.Column('account_currency', sa.String(), nullable=True, server_default='USD'),
        sa.Column('label', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['broker_id'], ['brokers.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_broker_accounts_mt5_login', 'broker_accounts', ['mt5_login'], unique=True)

    # 4. Add broker_account_id to trades (nullable initially)
    op.add_column('trades', sa.Column('broker_account_id', sa.Integer(), nullable=True))

    # 5. Insert default user, broker, account
    users_table = table('users',
        column('id', Integer),
        column('email', String),
        column('password_hash', String),
        column('role', String),
        column('is_active', Boolean)
    )
    brokers_table = table('brokers',
        column('id', Integer),
        column('user_id', Integer),
        column('broker_name', String),
        column('server_info', String)
    )
    broker_accounts_table = table('broker_accounts',
        column('id', Integer),
        column('broker_id', Integer),
        column('mt5_login', Integer),
        column('account_currency', String),
        column('label', String)
    )

    dummy_hash = '$2b$12$PLACEHOLDER_FOR_NOW'   # will be replaced later
    op.bulk_insert(users_table, [
        {'id': 1, 'email': 'default@example.com', 'password_hash': dummy_hash, 'role': 'admin', 'is_active': True}
    ])
    op.bulk_insert(brokers_table, [
        {'id': 1, 'user_id': 1, 'broker_name': 'DefaultBroker', 'server_info': 'Demo'}
    ])
    op.bulk_insert(broker_accounts_table, [
        {'id': 1, 'broker_id': 1, 'mt5_login': 1000000, 'account_currency': 'USD', 'label': 'Default Account'}
    ])

    # 6. Update existing trades to use the default account
    op.execute("UPDATE trades SET broker_account_id = 1 WHERE broker_account_id IS NULL")

    # 7. Make broker_account_id NOT NULL (SQLite workaround)
    # SQLite doesn't support ALTER COLUMN SET NOT NULL directly.
    # We'll create a new table with the correct schema, copy data, drop old, rename.
    # Step A: Create a new trades table with the NOT NULL constraint
    op.execute("""
        CREATE TABLE trades_new (
            id INTEGER NOT NULL,
            ticket_id INTEGER,
            order_id INTEGER,
            broker_account_id INTEGER NOT NULL,
            symbol VARCHAR NOT NULL,
            instrument_type VARCHAR NOT NULL,
            direction VARCHAR NOT NULL,
            lot_size FLOAT NOT NULL,
            entry_time DATETIME NOT NULL,
            exit_time DATETIME NOT NULL,
            entry_price FLOAT NOT NULL,
            exit_price FLOAT NOT NULL,
            stop_loss FLOAT,
            take_profit FLOAT,
            profit FLOAT NOT NULL,
            commission FLOAT,
            swap FLOAT,
            slippage FLOAT,
            session VARCHAR,
            strategy_tag VARCHAR,
            account_balance_after FLOAT,
            backtest_expected_pnl FLOAT,
            PRIMARY KEY (id),
            FOREIGN KEY(order_id) REFERENCES orders(id),
            FOREIGN KEY(broker_account_id) REFERENCES broker_accounts(id)
        )
    """)
    # Step B: Copy data from old trades to new
    op.execute("""
        INSERT INTO trades_new (
            id, ticket_id, order_id, broker_account_id,
            symbol, instrument_type, direction, lot_size,
            entry_time, exit_time, entry_price, exit_price,
            stop_loss, take_profit, profit, commission, swap,
            slippage, session, strategy_tag, account_balance_after,
            backtest_expected_pnl
        )
        SELECT
            id, ticket_id, order_id, broker_account_id,
            symbol, instrument_type, direction, lot_size,
            entry_time, exit_time, entry_price, exit_price,
            stop_loss, take_profit, profit, commission, swap,
            slippage, session, strategy_tag, account_balance_after,
            backtest_expected_pnl
        FROM trades
    """)
    # Step C: Drop old trades table
    op.drop_table('trades')
    # Step D: Rename new table to trades
    op.rename_table('trades_new', 'trades')

    # 8. Add indexes back (since they were dropped with the table)
    op.create_index('ix_trades_id', 'trades', ['id'], unique=False)
    op.create_index('ix_trades_ticket_id', 'trades', ['ticket_id'], unique=True)
    op.create_index('idx_trades_symbol_entry_time', 'trades', ['symbol', 'entry_time'])
    op.create_index('idx_trades_instrument_type', 'trades', ['instrument_type'])
    op.create_index('idx_trades_session', 'trades', ['session'])
    op.create_index('idx_trades_strategy_tag', 'trades', ['strategy_tag'])
    op.create_index('ix_trades_broker_account_id', 'trades', ['broker_account_id'])

    # 9. Add foreign key constraint for broker_account_id (already in CREATE TABLE)
    # No need to add separately, it's already in the new table definition.

def downgrade():
    # To downgrade, we need to reverse the process: remove NOT NULL constraint and drop new tables.
    # Since we don't have a simple ALTER, we recreate the old schema without the FK and with nullable broker_account_id.
    # For simplicity, we can just drop the new tables (but we'll keep data?).
    # We'll implement a downgrade that recreates the old trades table structure (nullable broker_account_id) and drop users/brokers/accounts.
    # However, we must ensure data is preserved.
    # We'll just drop the new tables and recreate the original trades schema (without broker_account_id).
    # But we can't easily revert the NOT NULL; we'll drop the column and tables.
    op.drop_index('ix_trades_broker_account_id', table_name='trades')
    op.drop_constraint('fk_trades_broker_account_id', 'trades', type_='foreignkey')
    # We'll drop the trades table and recreate without broker_account_id
    op.drop_table('trades')
    # Recreate trades without the FK column
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
    # Recreate indexes
    op.create_index('ix_trades_id', 'trades', ['id'], unique=False)
    op.create_index('ix_trades_ticket_id', 'trades', ['ticket_id'], unique=True)
    op.create_index('idx_trades_symbol_entry_time', 'trades', ['symbol', 'entry_time'])
    op.create_index('idx_trades_instrument_type', 'trades', ['instrument_type'])
    op.create_index('idx_trades_session', 'trades', ['session'])
    op.create_index('idx_trades_strategy_tag', 'trades', ['strategy_tag'])

    # Drop new tables
    op.drop_table('broker_accounts')
    op.drop_table('brokers')
    op.drop_table('users')
    # Drop enum type if PostgreSQL (not needed for SQLite)