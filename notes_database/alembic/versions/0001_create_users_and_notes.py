"""Initial migration: create users and notes tables"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

# PUBLIC_INTERFACE
def upgrade():
    """Create users and notes tables."""
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=50), nullable=False, unique=True, index=True),
        sa.Column("hashed_password", sa.String(length=128), nullable=False),
    )
    op.create_table(
        "notes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    )

# PUBLIC_INTERFACE
def downgrade():
    """Drop notes and users tables."""
    op.drop_table("notes")
    op.drop_table("users")
