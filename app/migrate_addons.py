import os
from sqlalchemy import create_engine, text
import sys


def migrate():
    """
    Migration script to add type column to add_ons table
    """
    try:
        # Construct database URL from individual environment variables
        db_user = os.getenv("DATABASE_USER", "postgres")
        db_password = os.getenv("DATABASE_PASSWORD", "postgres")
        db_host = os.getenv("DATABASE_HOST", "localhost")
        db_port = os.getenv("DATABASE_PORT", "5432")
        db_name = os.getenv("DATABASE_NAME", "tote")

        # Build the connection string
        database_url = (
            f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        )

        # Create engine
        engine = create_engine(database_url)

        # Execute migration
        with engine.connect() as conn:
            # Check if column already exists
            try:
                result = conn.execute(
                    text(
                        "SELECT 1 FROM information_schema.columns WHERE table_name='add_ons' AND column_name='type'"
                    )
                )
                if not result.fetchone():
                    print("Adding 'type' column to add_ons table...")
                    conn.execute(text("ALTER TABLE add_ons ADD COLUMN type VARCHAR"))
                    conn.commit()
                    print("Migration completed successfully.")
                else:
                    print(
                        "Column 'type' already exists in add_ons table. No migration needed."
                    )
            except Exception as e:
                print(f"Error checking or altering table: {e}")
                return False
        return True
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return False


if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)
