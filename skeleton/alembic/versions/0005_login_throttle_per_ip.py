"""login_throttles: (username, client_ip) 칸별 잠금

Revision ID: 0005_login_throttle_per_ip
Revises: 0004_notices_banners
Create Date: 2026-11-26 00:00:00

계정 단위 잠금을 (username, 접속 IP) 칸 단위 잠금 + username 전체 합산 칸("*")으로 바꾼다.
- 기존 행은 전체 합산 칸(client_ip="*")으로 옮긴다 — 진행 중인 잠금이 사라지지 않는다.
- username 단독 유일 인덱스를 지우고 (username, client_ip) 유일 제약을 둔다.
downgrade 는 IP 칸 행을 지우고(되돌릴 칸이 없다) 합산 칸만 계정 단위 행으로 되돌린다.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_login_throttle_per_ip"
down_revision: str | None = "0004_notices_banners"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

GLOBAL_KEY = "*"  # user_service.GLOBAL_THROTTLE_KEY 와 같아야 한다(마이그레이션은 앱 코드를 import 하지 않는다).


def upgrade() -> None:
    op.drop_index(op.f("ix_login_throttles_username"), table_name="login_throttles")
    # 기존 행을 채우려고 server_default 로 추가한 뒤 기본값을 지운다 — 모델에는 기본값이 없다.
    op.add_column(
        "login_throttles",
        sa.Column("client_ip", sa.String(length=64), nullable=False, server_default=GLOBAL_KEY),
    )
    op.alter_column("login_throttles", "client_ip", server_default=None)
    op.create_unique_constraint(
        "uq_login_throttles_username_client_ip", "login_throttles", ["username", "client_ip"]
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM login_throttles WHERE client_ip <> :g").bindparams(g=GLOBAL_KEY))
    op.drop_constraint("uq_login_throttles_username_client_ip", "login_throttles", type_="unique")
    op.drop_column("login_throttles", "client_ip")
    op.create_index(op.f("ix_login_throttles_username"), "login_throttles", ["username"], unique=True)
