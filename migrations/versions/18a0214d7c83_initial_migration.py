"""Initial migration

Revision ID: 18a0214d7c83
Revises: 
Create Date: 2024-09-17 18:40:17.751162

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '18a0214d7c83'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('user',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(length=120), nullable=False),
    sa.Column('api_token', sa.String(length=64), nullable=True),
    sa.Column('openai_api_key', sa.String(length=256), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email')
    )
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_user_api_token'), ['api_token'], unique=True)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_user_api_token'))

    op.drop_table('user')
    # ### end Alembic commands ###