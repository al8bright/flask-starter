"""운영 관리 명령줄 도구 (ARCHITECTURE.md §9 배포 체크리스트).

운영(APP_ENV=production)에서는 기본 관리자 시드가 금지되므로 관리자 계정 생성과 비밀번호
재설정을 이 도구로 한다. 비밀번호는 명령줄 인자로 받지 않는다(셸 기록·프로세스 목록 노출 방지)
— 대화형 입력(getpass) 또는 --password-stdin 으로만 받는다.

사용 예 (backend 디렉터리에서):
    python -m app.cli create-admin --username ops-admin
    python -m app.cli set-password --username admin
    echo "$NEW_PASSWORD" | python -m app.cli set-password --username admin --password-stdin
"""
import argparse
import getpass
import sys

from app.models.user import UserRole
from app.services import user_service
from app.services.exceptions import ServiceError


def _read_password(from_stdin: bool) -> str:
    if from_stdin:
        password = sys.stdin.readline().rstrip("\r\n")
        if not password:
            raise SystemExit("표준 입력에서 비밀번호를 읽지 못했습니다.")
        return password
    password = getpass.getpass("새 비밀번호: ")
    if password != getpass.getpass("비밀번호 확인: "):
        raise SystemExit("두 비밀번호가 일치하지 않습니다.")
    return password


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.cli", description="운영 관리 명령")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (
        ("create-admin", "관리자 계정을 만든다"),
        ("set-password", "비밀번호를 재설정하고 해당 사용자의 모든 세션을 폐기한다"),
    ):
        cmd = sub.add_parser(name, help=help_text)
        cmd.add_argument("--username", required=True)
        cmd.add_argument(
            "--password-stdin", action="store_true", help="비밀번호를 표준 입력 첫 줄에서 읽는다"
        )
    return parser


def main(argv: list[str] | None = None, *, session_factory=None) -> int:
    args = _build_parser().parse_args(argv)
    password = _read_password(args.password_stdin)
    if session_factory is None:
        from app.db.session import SessionLocal

        session_factory = SessionLocal
    try:
        with session_factory() as db:
            if args.command == "create-admin":
                user_service.create_user(
                    db, username=args.username, password=password, role=UserRole.ADMIN
                )
                print(f"관리자 계정을 만들었습니다: {args.username}")
            else:
                user_service.set_password(db, username=args.username, password=password)
                print(f"비밀번호를 재설정하고 세션을 모두 폐기했습니다: {args.username}")
    except (ServiceError, ValueError) as e:
        print(f"실패: {getattr(e, 'message', e)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
