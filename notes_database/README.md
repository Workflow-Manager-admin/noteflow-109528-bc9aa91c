# notes_database

This container provides the database setup for the Noteflow application.

## Features

- PostgreSQL database for persistent storage.
- Tables for users (authentication) and notes (CRUD).
- SQLAlchemy models and Alembic migrations for schema management.

## Usage

1. Configure the environment variables for database access.
2. Run migrations to initialize or upgrade the database schema.
3. The backend will connect to this database for user and note management.
