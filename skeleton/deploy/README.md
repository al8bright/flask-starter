# 운영 배포 예시 — Linux + nginx + gunicorn(systemd)

한 대의 Linux 서버(Ubuntu 기준)에 nginx 가 HTTPS 를 받고 gunicorn 으로 넘기는 구성의 예시다.
다른 구성(컨테이너, 관리형 플랫폼)을 쓰면 이 폴더를 지워도 된다. 배포 전 확인 목록은 `ARCHITECTURE.md` §21 「배포 전 체크리스트」다.

| 파일 | 역할 |
|---|---|
| `app.service` | systemd 서비스 — gunicorn `127.0.0.1:8000` |
| `nginx.conf` | nginx 사이트 — 요청 제한(`/login` 은 더 좁게), 본문 상한, gzip, 프록시 |
| `nginx-proxy.conf` | 프록시 공통 설정 — `Host`·`X-Forwarded-*` 전달 |
| `deploy.sh` | 갱신 배포 — pull → pip → CSS → alembic → 재기동 → 상태 확인 |

예시의 가정은 다음과 같다. 다르면 각 파일 머리 주석을 보고 함께 수정한다. 요청 제한·워커 수·타임아웃은 출발점일 뿐이므로 서비스에 맞게 정한다.
⛔ 프로젝트 저장소가 공개라면 실제 운영 도메인·서버 경로·계정·요청 제한 값을 이 폴더에 커밋하지 않는다 — 공격 단서가 된다. 서버에서만 고쳐 쓴다.

- 코드 위치 `/srv/__PROJECT_SNAKE__`, 배포 계정 `deploy`(코드 폴더 소유자, `sudo` 가능)
- 서비스 이름 `__PROJECT_SNAKE__`, 앱 포트 `8000`(외부에 열지 않는다)
- 도메인 `app.example.com`

## 최초 설치

1. **DNS** — 도메인의 A 레코드를 서버 공인 IP 로 둔다.
2. **DB** — 관리자 계정으로 접속해 앱 전용 계정과 데이터베이스를 생성한다. 앱 계정은 superuser 가 아니어야 한다.

   ```sql
   CREATE ROLE __PROJECT_SNAKE__ LOGIN PASSWORD '<DB 비밀번호>';
   CREATE DATABASE __PROJECT_SNAKE__ OWNER __PROJECT_SNAKE__;
   REVOKE ALL ON DATABASE __PROJECT_SNAKE__ FROM PUBLIC;
   ALTER DATABASE __PROJECT_SNAKE__ SET timezone TO 'Asia/Seoul';
   ```

3. **코드** — `/srv/__PROJECT_SNAKE__` 에 저장소를 clone 한다(배포 계정 소유).
4. **운영 `.env`** — `.env.example` 을 복사해 아래 값을 바꾸고 `chmod 600 .env` 한다. ⛔ 커밋하지 않는다.

   | 키 | 운영 값 |
   |---|---|
   | `APP_ENV` | `production` |
   | `DATABASE_URL` | 2단계의 계정·비밀번호·데이터베이스 |
   | `SECRET_KEY` | 새 무작위 값(`openssl rand -hex 32`) |
   | `COOKIE_SECURE` | `true` |
   | `TRUSTED_PROXY_HOPS` | `1`(nginx 한 겹) |
   | `SEED_DEFAULT_ADMIN` | `false` |
   | `BCRYPT_ROUNDS` | 주석 처리(기본 12) 또는 12 이상 |

5. **venv·패키지·CSS·마이그레이션**

   ```bash
   python3.13 -m venv .venv
   .venv/bin/python -m pip install -r requirements.txt
   .venv/bin/python -m pip check
   ./scripts/tailwind.sh
   .venv/bin/alembic upgrade head
   ```

6. **서비스** — `app.service` 의 `User`·`Group` 을 배포 계정으로 맞춘 뒤 머리 주석의 명령으로 설치·기동한다.
7. **nginx·인증서** — `nginx.conf` 의 `server_name` 을 실제 도메인으로 바꾸고 머리 주석의 순서대로 설치한다. `nginx -t` 가 통과할 때만 reload 한다. 인증서는 certbot 이 이 파일에 443 블록을 추가한다.
8. **관리자 계정** — `.venv/bin/python -m app.cli create-admin --username <이름>`(비밀번호는 대화형 입력).
9. **확인**
   - `curl https://<도메인>/api/v1/health/db` 가 200 이다.
   - 응답 헤더에 `Strict-Transport-Security`·`Content-Security-Policy` 가 있고, 로그인 쿠키에 `Secure` 가 붙는다.
   - 브라우저 개발자 도구 콘솔에 CSP 위반이 없다.
   - 기동 로그(`journalctl -u __PROJECT_SNAKE__`)에 `TRUSTED_PROXY_HOPS` 경고가 없다.

## 갱신 배포

```bash
cd /srv/__PROJECT_SNAKE__ && ./deploy/deploy.sh
```

한 단계라도 실패하면 그 자리에서 멈추고 서비스는 재기동하지 않는다. 마이그레이션이 이미 적용된 뒤 상태 확인이 실패하면
`journalctl -u __PROJECT_SNAKE__ -n 50 --no-pager` 로 원인을 확인한다. 되돌릴 때는 이전 커밋으로 checkout 하고,
그 커밋 이후의 마이그레이션이 있으면 `alembic downgrade <리비전>` 을 먼저 실행한다(§11).

## 운영 중 확인

- 로그: `journalctl -u __PROJECT_SNAKE__`(감사 로그 `app.audit` 포함 — §9)
- 백업: DB 덤프(`pg_dump`)와 업로드 폴더(`UPLOAD_DIR`, 기본 `uploads/`)를 함께 보관한다.
