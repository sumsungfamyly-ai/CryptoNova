"""Idempotent schema + integrity triggers. Used by POST /internal/bootstrap (Vercel has no release step)."""
from novaapi.core.db import engine
from novaapi.models import Base

TYPES = "('transfer','admin_credit','admin_debit','issuance','initial_grant','fee','swap_in','swap_out')"
STATEMENTS = [
    """CREATE OR REPLACE FUNCTION ledger_zero_sum_check() RETURNS trigger AS $$
    BEGIN
      IF EXISTS (SELECT 1 FROM ledger_entries WHERE transaction_id = NEW.transaction_id
                 GROUP BY asset_id HAVING SUM(amount) <> 0) THEN
        RAISE EXCEPTION USING MESSAGE = 'ledger imbalance', ERRCODE = 'check_violation';
      END IF;
      RETURN NULL;
    END; $$ LANGUAGE plpgsql""",
    "DROP TRIGGER IF EXISTS trg_ledger_zero_sum ON ledger_entries",
    """CREATE CONSTRAINT TRIGGER trg_ledger_zero_sum AFTER INSERT ON ledger_entries
       DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION ledger_zero_sum_check()""",
    """CREATE OR REPLACE FUNCTION forbid_mutation() RETURNS trigger AS $$
    BEGIN
      RAISE EXCEPTION USING MESSAGE = 'append-only table ' || TG_TABLE_NAME, ERRCODE = 'restrict_violation';
    END; $$ LANGUAGE plpgsql""",
    "DROP TRIGGER IF EXISTS trg_ledger_entries_immutable ON ledger_entries",
    """CREATE TRIGGER trg_ledger_entries_immutable BEFORE UPDATE OR DELETE ON ledger_entries
       FOR EACH ROW EXECUTE FUNCTION forbid_mutation()""",
    "DROP TRIGGER IF EXISTS trg_admin_logs_immutable ON admin_logs",
    """CREATE TRIGGER trg_admin_logs_immutable BEFORE UPDATE OR DELETE ON admin_logs
       FOR EACH ROW EXECUTE FUNCTION forbid_mutation()""",
    "ALTER TABLE transactions DROP CONSTRAINT IF EXISTS ck_transactions_type_valid",
    f"ALTER TABLE transactions ADD CONSTRAINT ck_transactions_type_valid CHECK (type IN {TYPES})",
]


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)  # creates only missing tables
        for st in STATEMENTS:
            await conn.exec_driver_sql(st)
