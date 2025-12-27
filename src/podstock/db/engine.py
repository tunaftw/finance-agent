"""Database engine and session management."""

from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

# Default database path
DEFAULT_DB_PATH = Path(__file__).parent.parent.parent.parent / "data" / "podstock.db"


def get_engine(db_path: Path | str | None = None, echo: bool = False) -> Engine:
    """Create SQLAlchemy engine for SQLite database.

    Args:
        db_path: Path to database file. Defaults to data/podstock.db
        echo: If True, log all SQL statements

    Returns:
        SQLAlchemy Engine instance
    """
    if db_path is None:
        db_path = DEFAULT_DB_PATH

    db_path = Path(db_path)

    # Ensure parent directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(
        f"sqlite:///{db_path}",
        echo=echo,
        connect_args={"check_same_thread": False},
    )

    # Enable foreign keys for every connection
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


# Global session factory (lazy initialized)
_session_factory: sessionmaker | None = None


def get_session_factory(engine: Engine | None = None) -> sessionmaker:
    """Get or create session factory.

    Args:
        engine: SQLAlchemy engine. If None, creates default engine.

    Returns:
        Session factory
    """
    global _session_factory

    if _session_factory is None or engine is not None:
        if engine is None:
            engine = get_engine()
        _session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    return _session_factory


@contextmanager
def get_session(engine: Engine | None = None) -> Generator[Session, None, None]:
    """Context manager for database sessions.

    Usage:
        with get_session() as session:
            results = session.query(Recommendation).all()

    Args:
        engine: Optional engine. Uses default if not provided.

    Yields:
        SQLAlchemy Session
    """
    factory = get_session_factory(engine)
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db(engine: Engine | None = None, force: bool = False) -> None:
    """Initialize database schema.

    Reads schema.sql and executes it to create all tables.

    Args:
        engine: SQLAlchemy engine. Creates default if not provided.
        force: If True, drop existing tables first
    """
    if engine is None:
        engine = get_engine()

    schema_path = Path(__file__).parent / "schema.sql"

    if not schema_path.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_path}")

    schema_sql = schema_path.read_text()

    with engine.connect() as conn:
        if force:
            # Drop all tables in reverse dependency order
            tables = [
                "load_log",
                "recommendation_performance",
                "prices",
                "key_takeaways",
                "mentions",
                "recommendations",
                "pending_securities",
                "security_relations",
                "security_aliases",
                "securities",
                "analyses",
                "content",
                "sources",
            ]
            for table in tables:
                conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
            conn.execute(text("DROP VIEW IF EXISTS current_analyses"))
            conn.commit()

        # Parse and execute statements properly
        # Remove comments and split by semicolons
        statements = []
        current_statement = []

        for line in schema_sql.split("\n"):
            # Skip pure comment lines
            stripped = line.strip()
            if stripped.startswith("--"):
                continue
            # Remove inline comments
            if "--" in line:
                line = line[: line.index("--")]
            current_statement.append(line)

            # Check if statement ends
            if ";" in line:
                stmt = "\n".join(current_statement).strip()
                if stmt and stmt != ";":
                    # Remove trailing semicolon for execution
                    stmt = stmt.rstrip(";").strip()
                    if stmt:
                        statements.append(stmt)
                current_statement = []

        # Execute each statement
        for stmt in statements:
            if stmt:
                conn.execute(text(stmt))

        conn.commit()


def reset_session_factory() -> None:
    """Reset the global session factory. Useful for testing."""
    global _session_factory
    _session_factory = None
