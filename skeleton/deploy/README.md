# 운영 배포 예시 — Linux + nginx + gunicorn(systemd)

한 대의 Linux 서버(Ubuntu 24.04 기준)에 nginx 가 HTTPS 를 받고 gunicorn 유닉스 소켓으로 넘기는 구성의 예시다.
다른 구성(컨테이너, 관리형 플랫폼)을 쓰면 이 폴더를 지워도 된다. 배포 전 확인 목록은 `ARCHITECTURE.md` §21 「배포 전 체크리스트」다.

| 파일 | 역할 |
|---|---|
| `app.service` | systemd 서비스 — 전용 계정으로 gunicorn 실행, 유닉스 소켓, 쓰기 경로·권한 격리 |
| `nginx.conf` | nginx 사이트 — 알 수 없는 Host 차단, 요청 제한(`/login` 은 더 좁게), 경로별 본문 상한, 내부 헬스 체크 차단, gzip |
| `nginx-proxy.conf` | 프록시 공통 설정 — `Host`·`X-Forwarded-*` 전달(`/etc/nginx/snippets/` 에 사본으로 설치) |
| `deploy.sh` | 갱신 배포 — pull → pip(해시 검증) → CSS → alembic(소유 계정) → 재기동 → 상태 확인 |

예시의 가정은 다음과 같다. 다르면 각 파일 머리 주석을 보고 함께 수정한다. 요청 제한·워커 수·타임아웃·본문 상한은 출발점일 뿐이므로 서비스에 맞게 정한다.
⛔ 프로젝트 저장소가 공개라면 실제 운영 도메인·서버 경로·계정·요청 제한 값을 이 폴더에 커밋하지 않는다 — 공격 단서가 된다. 서버에서만 고쳐 쓴다.

| 항목 | 값 | 권한 |
|---|---|---|
| 배포 계정 | `deploy` — 코드 소유, `sudo` 가능, 그룹 `__PROJECT_SNAKE__` 에 속한다 | 사람이 로그인해 배포한다 |
| 앱 실행 계정 | `__PROJECT_SNAKE__` — 시스템 계정, 셸·`sudo`·홈 없음 | 코드는 읽기만, 업로드 폴더만 쓰기 |
| 코드 | `/srv/__PROJECT_SNAKE__` | `deploy:__PROJECT_SNAKE__` `0750`(안쪽 파일은 `deploy` 소유, 다른 사용자 읽기) |
| 운영 `.env` | `/srv/__PROJECT_SNAKE__/.env` | `root:__PROJECT_SNAKE__` `0640` |
| 마이그레이션 접속 정보 | `/etc/__PROJECT_SNAKE__/migrate.env` | `root:deploy` `0640`(앱 실행 계정은 읽지 못한다) |
| 업로드 | `/var/lib/__PROJECT_SNAKE__/uploads` | `__PROJECT_SNAKE__:__PROJECT_SNAKE__` `0750` |
| 앱 소켓 | `/run/__PROJECT_SNAKE__/gunicorn.sock` | 폴더 `__PROJECT_SNAKE__:www-data` `0750`(systemd 가 만든다) — TCP 포트를 열지 않는다 |
| DB 계정 | `__PROJECT_SNAKE___owner`(스키마 소유·마이그레이션) · `__PROJECT_SNAKE___app`(앱 — 데이터 읽기·쓰기만) | |
| 서비스 이름 · 도메인 | `__PROJECT_SNAKE__` · `app.example.com` | |

## 최초 설치

1. **계정·폴더** — 앱 실행 계정을 만들고 배포 계정을 그 그룹에 넣는다(`.env` 를 읽기 위해서다). 그룹 변경은 다시 로그인해야 적용된다.

   ```bash
   sudo useradd --system --user-group --home-dir /nonexistent --no-create-home \
     --shell /usr/sbin/nologin __PROJECT_SNAKE__
   sudo usermod -aG __PROJECT_SNAKE__ deploy
   sudo install -d -o deploy -g __PROJECT_SNAKE__ -m 0750 /srv/__PROJECT_SNAKE__
   sudo install -d -o __PROJECT_SNAKE__ -g __PROJECT_SNAKE__ -m 0750 /var/lib/__PROJECT_SNAKE__ /var/lib/__PROJECT_SNAKE__/uploads
   sudo install -d -o root -g deploy -m 0750 /etc/__PROJECT_SNAKE__
   ```

2. **DNS** — 도메인의 A 레코드를 서버 공인 IP 로 둔다.
3. **DB** — 소유 계정(테이블을 만들고 마이그레이션한다)과 앱 계정(데이터 읽기·쓰기만 한다)을 나눈다. 둘 다 superuser 가 아니다.
   비밀번호는 SQL 문에 쓰지 않고 psql 의 `\password` 로 입력한다(셸·psql 기록과 서버 로그에 남지 않는다).
   URL 에 넣기 쉽게 `openssl rand -hex 24` 처럼 영숫자만으로 만든다 — 특수문자를 쓰면 `DATABASE_URL` 에서 퍼센트 인코딩해야 한다.

   ```text
   $ sudo -u postgres psql
   CREATE ROLE __PROJECT_SNAKE___owner LOGIN;
   \password __PROJECT_SNAKE___owner
   CREATE ROLE __PROJECT_SNAKE___app LOGIN;
   \password __PROJECT_SNAKE___app
   CREATE DATABASE __PROJECT_SNAKE__ OWNER __PROJECT_SNAKE___owner;
   REVOKE ALL ON DATABASE __PROJECT_SNAKE__ FROM PUBLIC;
   GRANT CONNECT ON DATABASE __PROJECT_SNAKE__ TO __PROJECT_SNAKE___app;
   ALTER DATABASE __PROJECT_SNAKE__ SET timezone TO 'Asia/Seoul';
   \c __PROJECT_SNAKE__
   -- PostgreSQL 14 이하만: public 스키마에 누구나 테이블을 만들 수 있는 기본값을 없앤다(15 부터는 기본값이다).
   REVOKE CREATE ON SCHEMA public FROM PUBLIC;
   ALTER SCHEMA public OWNER TO __PROJECT_SNAKE___owner;
   -- 공통: 앱 계정은 DDL 없이 데이터만 다룬다. 소유 계정이 앞으로 만드는 테이블·시퀀스에도 자동으로 적용한다.
   GRANT USAGE ON SCHEMA public TO __PROJECT_SNAKE___app;
   ALTER DEFAULT PRIVILEGES FOR ROLE __PROJECT_SNAKE___owner IN SCHEMA public
     GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO __PROJECT_SNAKE___app;
   ALTER DEFAULT PRIVILEGES FOR ROLE __PROJECT_SNAKE___owner IN SCHEMA public
     GRANT USAGE, SELECT ON SEQUENCES TO __PROJECT_SNAKE___app;
   -- 이미 마이그레이션한 DB 에 나중에 적용할 때만: 기존 테이블·시퀀스에도 같은 권한을 준다.
   GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO __PROJECT_SNAKE___app;
   GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO __PROJECT_SNAKE___app;
   ```

   ⛔ 기본 권한(`ALTER DEFAULT PRIVILEGES`)은 소유 계정이 만드는 객체에만 적용된다. 마이그레이션은 항상 소유 계정으로 실행한다(`deploy.sh` 가 그렇게 한다).

4. **코드** — 배포 계정으로 `/srv/__PROJECT_SNAKE__` 에 저장소를 clone 한다. 앱 실행 계정이 새 파일을 읽을 수 있게 `umask 0022` 로 작업한다.

   ```bash
   umask 0022 && git clone <저장소 URL> /srv/__PROJECT_SNAKE__
   ```

5. **운영 `.env`** — `.env.example` 을 복사해 아래 값을 바꾸고 권한을 좁힌다. 이후 수정은 `sudoedit` 로 한다. ⛔ 커밋하지 않는다.

   ```bash
   cd /srv/__PROJECT_SNAKE__ && cp .env.example .env   # 아래 표대로 고친 뒤
   sudo chown root:__PROJECT_SNAKE__ .env && sudo chmod 0640 .env
   ```

   | 키 | 운영 값 |
   |---|---|
   | `APP_ENV` | `production`(`deploy.sh` 가 이 값이 아니면 멈춘다) |
   | `DATABASE_URL` | 앱 계정 `__PROJECT_SNAKE___app` 의 접속 정보 — 소유 계정을 넣지 않는다 |
   | `SECRET_KEY` | 새 무작위 값(`openssl rand -hex 32`) |
   | `COOKIE_SECURE` | `true` |
   | `TRUSTED_PROXY_HOPS` | `1`(nginx 한 겹) |
   | `SEED_DEFAULT_ADMIN` | `false` |
   | `BCRYPT_ROUNDS` | 주석 처리(기본 12) 또는 12 이상 |
   | `UPLOAD_DIR` | `/var/lib/__PROJECT_SNAKE__/uploads`(`app.service` 의 `ReadWritePaths` 와 같게) |
   | `LOGIN_MAX_FAILURES` · `LOGIN_LOCKOUT_MINUTES` | 서비스에 맞게 정한다(기본 5회 · 15분). 계정 단위 잠금이라 값을 낮추고 잠금을 길게 하면 대입 공격은 느려지지만, 아이디를 아는 사람이 정상 사용자를 잠글 수도 있다. IP 단위 제한은 nginx 가 맡는다 |

6. **마이그레이션 접속 정보** — 소유 계정의 URL 을 `/etc/__PROJECT_SNAKE__/migrate.env` 에 한 줄로 둔다. `deploy.sh` 가 Alembic 을 실행할 때만 이 값으로 `.env` 의 `DATABASE_URL` 을 덮는다(프로세스 환경변수가 `.env` 보다 우선한다).

   ```bash
   sudoedit /etc/__PROJECT_SNAKE__/migrate.env   # DATABASE_URL=postgresql+psycopg2://__PROJECT_SNAKE___owner:<비밀번호>@localhost:5432/__PROJECT_SNAKE__
   sudo chown root:deploy /etc/__PROJECT_SNAKE__/migrate.env && sudo chmod 0640 /etc/__PROJECT_SNAKE__/migrate.env
   ```

7. **venv·패키지·CSS·마이그레이션**(배포 계정, 프로젝트 루트)

   ```bash
   umask 0022
   python3.13 -m venv .venv
   .venv/bin/python -m pip install --require-hashes -r requirements.lock
   ./scripts/tailwind.sh
   DATABASE_URL="$(sed -n 's/^DATABASE_URL=//p' /etc/__PROJECT_SNAKE__/migrate.env)" .venv/bin/alembic upgrade head
   ```

8. **서비스** — `app.service` 머리 주석의 명령으로 root 소유 사본을 설치하고 기동한다. 실행 계정·경로를 바꿨으면 `User`·`Group`·`ReadWritePaths`·소켓 경로를 함께 고친다.
9. **nginx·인증서** — `nginx.conf` 의 `server_name` 을 실제 도메인으로 바꾸고 머리 주석의 순서대로 설치한다(`nginx-proxy.conf` 도 `/etc/nginx/snippets/` 에 사본으로 설치한다). `nginx -t` 가 통과할 때만 reload 한다. 인증서는 certbot 이 앱 server 블록에 443 설정을 추가한다.
10. **관리자 계정** — `.venv/bin/python -m app.cli create-admin --username <이름>`(비밀번호는 대화형 입력).
    아이디는 `admin`·`administrator`·`root`·서비스 이름처럼 짐작하기 쉬운 값을 피한다 — 로그인 잠금이 계정 단위라 아이디를 아는 사람은 대입을 시도하거나 그 계정을 잠글 수 있다.
11. **확인**
    - `curl https://<도메인>/api/v1/health` 가 200 이고, `curl https://<도메인>/api/v1/health/db` 는 404 다(내부 전용).
    - `sudo -u www-data curl --unix-socket /run/__PROJECT_SNAKE__/gunicorn.sock http://localhost/api/v1/health/db` 가 `{"db": "ok", …}` 다.
    - IP 로 직접 접속하면 연결이 끊기고(80 은 응답 없음, 443 은 TLS 거부), 응답 헤더에 nginx 버전이 없다.
    - 응답 헤더에 `Strict-Transport-Security`·`Content-Security-Policy` 가 있고, 로그인 쿠키에 `Secure` 가 붙는다.
    - 브라우저 개발자 도구 콘솔에 CSP 위반이 없다. 편집기 이미지·배너·첨부 업로드가 되고, 1 MB 를 넘는 요청이 다른 경로에서는 413 이다.
    - 기동 로그(`journalctl -u __PROJECT_SNAKE__`)에 `TRUSTED_PROXY_HOPS` 경고나 권한 오류가 없다. `sudo systemd-analyze security __PROJECT_SNAKE__` 로 격리 수준을 본다.

## 갱신 배포

```bash
cd /srv/__PROJECT_SNAKE__ && ./deploy/deploy.sh
```

root 로 실행하거나 `.env` 의 `APP_ENV` 가 `production` 이 아니면 아무것도 하지 않고 멈춘다. 한 단계라도 실패하면 그 자리에서 멈추고 서비스는 재기동하지 않는다.
마이그레이션이 이미 적용된 뒤 상태 확인이 실패하면 `journalctl -u __PROJECT_SNAKE__ -n 50 --no-pager` 로 원인을 확인한다. 되돌릴 때는 이전 커밋으로 checkout 하고,
그 커밋 이후의 마이그레이션이 있으면 소유 계정으로 `alembic downgrade <리비전>` 을 먼저 실행한다(§11).
`nginx.conf`·`nginx-proxy.conf`·`app.service` 를 고친 커밋은 `deploy.sh` 가 반영하지 않는다 — 최초 설치의 설치 명령으로 사본을 다시 설치한다.

## 운영 중 확인

- 로그: `journalctl -u __PROJECT_SNAKE__`(감사 로그 `app.audit` 포함 — §9)
- 백업: DB 덤프(`pg_dump`, 소유 계정 또는 관리자)와 업로드 폴더(`/var/lib/__PROJECT_SNAKE__/uploads`)를 함께 보관한다.
