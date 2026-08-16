from sqlalchemy import create_engine, inspect, text

DATABASE_URL = "sqlite:////data/syncchat.db"

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:

    inspector = inspect(conn)

    columns = {
        column["name"]
        for column in inspector.get_columns("messages")
    }

    print("Existing columns:")
    print(columns)

    if "message_type" not in columns:
        print("Adding message_type...")
        conn.execute(
            text(
                "ALTER TABLE messages "
                "ADD COLUMN message_type VARCHAR DEFAULT 'text'"
            )
        )
    else:
        print("message_type already exists")

    if "media_url" not in columns:
        print("Adding media_url...")
        conn.execute(
            text(
                "ALTER TABLE messages "
                "ADD COLUMN media_url VARCHAR"
            )
        )
    else:
        print("media_url already exists")

    if "duration" not in columns:
        print("Adding duration...")
        conn.execute(
            text(
                "ALTER TABLE messages "
                "ADD COLUMN duration FLOAT"
            )
        )
    else:
        print("duration already exists")

    conn.commit()

print("Migration completed successfully.")