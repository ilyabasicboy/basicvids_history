from basicvids_history.db import create_db_and_tables, engine
from basicvids_history.main import app

create_db_and_tables()

__all__ = ["app", "engine"]
