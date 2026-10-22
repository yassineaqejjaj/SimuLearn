from app.db import get_engine, session_scope
from app.models import Base
from app.seed import seed_demo

if __name__ == "__main__":
    Base.metadata.create_all(get_engine())  # dev rapide ; en prod : `alembic upgrade head`
    with session_scope() as db:
        print(seed_demo(db))
