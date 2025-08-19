"""
정적 파일 템플릿들
"""
from textwrap import dedent

STYLES_CSS = dedent(
    """
    /* Add your styles here */
    .container { max-width: 900px; margin: 0 auto; padding: 1rem; }
    """
)

APP_JS = """// Add your JS here\nconsole.log('App loaded');\n"""

README = dedent(
    """
    # __PROJECT_NAME__

    Flask 기반 게시판 애플리케이션 (CRUD + 파일 업로드 + 인증)

    ## 기능

    - 🔐 사용자 인증 (로그인/로그아웃)
    - 📝 게시글 CRUD (생성/조회/수정/삭제)
    - 📁 파일 업로드 및 다운로드
    - 🎨 Tailwind CSS UI
    - ⚡ Flask-Caching
    - 🔄 환경별 설정 (개발/테스트/프로덕션)

    ## 설치 및 실행

    ```bash
    # 1) 가상환경 활성화
    # macOS/Linux
    source venv/bin/activate
    # Windows
    venv\\Scripts\\activate

    # 2) 데이터베이스 마이그레이션
    flask db upgrade

    # 3) 애플리케이션 실행
    flask run
    # 또는
    python wsgi.py
    ```

    ## 환경 설정

    `.env` 파일에서 다음 설정을 변경할 수 있습니다:

    ```env
    FLASK_ENV=development  # development, testing, production
    DATABASE_URL=sqlite:///app.db
    SECRET_KEY=your-secret-key
    ```

    ## 기본 사용자

    - 사용자명: admin
    - 비밀번호: admin123

    ## 프로젝트 구조

    ```
    app/
    ├── config.py          # 환경별 설정
    ├── extensions.py      # Flask 확장
    ├── routes/           # 라우트 블루프린트
    ├── models/           # 데이터베이스 모델
    ├── services/         # 비즈니스 로직
    ├── utils/            # 유틸리티 함수
    ├── templates/        # HTML 템플릿
    ├── static/           # 정적 파일
    └── uploads/          # 업로드된 파일
    ```
    """
)
