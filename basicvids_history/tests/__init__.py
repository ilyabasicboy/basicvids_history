import os
import tempfile


test_data_path = tempfile.mkdtemp(prefix="basicvids_history_tests_")
os.environ["DATA_PATH"] = test_data_path
os.environ["DATABASE_URL"] = f"sqlite:///{test_data_path}/database.db"

from basicvids_history.db import create_db_and_tables, engine
from basicvids_history.main import app

create_db_and_tables()

__all__ = ["app", "engine"]
