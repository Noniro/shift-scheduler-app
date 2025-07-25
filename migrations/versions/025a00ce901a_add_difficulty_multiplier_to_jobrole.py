"""Add difficulty_multiplier to JobRole

Revision ID: 025a00ce901a
Revises: 
Create Date: 2025-07-07 00:00:32.765060

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '025a00ce901a'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('shift_template')
    with op.batch_alter_table('job_role', schema=None) as batch_op:
        batch_op.add_column(sa.Column('difficulty_multiplier', sa.Float(), server_default='1.0', nullable=False))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('job_role', schema=None) as batch_op:
        batch_op.drop_column('difficulty_multiplier')

    op.create_table('shift_template',
    sa.Column('id', sa.INTEGER(), nullable=False),
    sa.Column('name', sa.VARCHAR(length=100), nullable=False),
    sa.Column('duration_days', sa.INTEGER(), nullable=False),
    sa.Column('duration_hours', sa.INTEGER(), nullable=False),
    sa.Column('duration_minutes', sa.INTEGER(), nullable=False),
    sa.Column('scheduling_period_id', sa.INTEGER(), nullable=False),
    sa.ForeignKeyConstraint(['scheduling_period_id'], ['scheduling_period.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###
