"""운영 관리 명령줄 도구 (ARCHITECTURE.md §9 배포 체크리스트).

운영(APP_ENV=production)에서는 기본 관리자 시드가 금지되므로 관리자 계정 생성과 비밀번호
재설정을 이 도구로 한다. 비밀번호는 명령줄 인자로 받지 않는다(셸 기록·프로세스 목록 노출 방지)
— 대화형 입력(getpass) 또는 --password-stdin 으로만 받는다.
cleanup-auth 는 쌓이는 인증 기록(만료·폐기 세션, 오래된 로그인 실패 칸)을 지운다 — cron 등으로 주기 실행한다.

사용 예 (backend 디렉터리에서):
    python -m app.cli create-admin --username ops-admin
    python -m app.cli set-password --username admin
    echo "$NEW_PASSWORD" | python -m app.cli set-password --username admin --password-stdin
    python -m app.cli cleanup-auth --dry-run
    python -m app.cli cleanup-auth --retention-days 7
"""
import argparse
import getpass
import sys
from datetime import timedelta

from app.models.user import UserRole
from app.services import session_service, user_service
from app.services.exceptions import ServiceError

PASSWORD_COMMANDS = ("create-admin", "set-password")


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


def _non_negative_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as e:
        raise argparse.ArgumentTypeError("0 이상의 정수여야 합니다.") from e
    if number < 0:
        raise argparse.ArgumentTypeError("0 이상의 정수여야 합니다.")
    return number


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
    cleanup = sub.add_parser(
        "cleanup-auth", help="만료·폐기된 세션과 오래된 로그인 실패 기록을 지운다"
    )
    cleanup.add_argument("--dry-run", action="store_true", help="지우지 않고 대상 건수만 출력한다")
    cleanup.add_argument(
        "--retention-days",
        type=_non_negative_int,
        default=0,
        help="만료·폐기 후 이 일수가 지난 세션만 지운다(기본 0 — 감사 추적이 필요하면 늘린다)",
    )
    return parser


def _cleanup_auth(db, *, dry_run: bool, retention_days: int) -> None:
    sessions = session_service.purge_inactive_sessions(
        db, retention=timedelta(days=retention_days), dry_run=dry_run
    )
    throttles = user_service.purge_stale_login_throttles(db, dry_run=dry_run)
    if dry_run:
        print(f"삭제 대상(--dry-run, 지우지 않음): 세션 {sessions}건, 로그인 실패 기록 {throttles}건")
    else:
        print(f"삭제했습니다: 세션 {sessions}건, 로그인 실패 기록 {throttles}건")


def main(argv: list[str] | None = None, *, session_factory=None) -> int:
    args = _build_parser().parse_args(argv)
    password = _read_password(args.password_stdin) if args.command in PASSWORD_COMMANDS else None
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
            elif args.command == "set-password":
                user_service.set_password(db, username=args.username, password=password)
                print(f"비밀번호를 재설정하고 세션을 모두 폐기했습니다: {args.username}")
            else:
                _cleanup_auth(db, dry_run=args.dry_run, retention_days=args.retention_days)
    except (ServiceError, ValueError) as e:
        print(f"실패: {getattr(e, 'message', e)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
