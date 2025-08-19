# Flask Builder 🚀

Flask 프로젝트를 빠르게 생성하는 스마트 스캐폴더입니다. 모듈화된 구조로 설계되어 확장 가능하고 유지보수가 용이합니다.

## ✨ 주요 기능

- **🎯 완전 자동화**: 프로젝트 구조, 가상환경, 패키지 설치까지 한 번에
- **🗄️ 다중 데이터베이스 지원**: PostgreSQL, MySQL, SQL Server, SQLite
- **🎨 모던 UI**: Tailwind CSS 기반의 반응형 웹 인터페이스
- **🔐 인증 시스템**: 로그인/로그아웃 기능 포함
- **📝 게시판 시스템**: CRUD 기능이 완비된 게시판
- **📁 파일 업로드**: 파일 업로드/다운로드 기능
- **📍 프로젝트 위치 선택**: 원하는 경로에 프로젝트 생성 가능

## 🚀 빠른 시작

```bash
# 저장소 클론
git clone https://github.com/yourusername/flask-builder.git
cd flask-builder

# 실행
python main.py
```

## 📋 사용법

1. **프로젝트 이름 입력** (예: `my_flask_app`)
2. **프로젝트 생성 경로 선택** (예: `P:\flask`)
3. **데이터베이스 설정**:
   - PostgreSQL, MySQL, SQL Server, SQLite 중 선택
   - 연결 정보 입력
4. **자동 생성 완료!**

## 🏗️ 생성되는 프로젝트 구조

```
my_flask_app/
├── app/
│   ├── __init__.py          # Flask 앱 팩토리
│   ├── config.py            # 설정 파일
│   ├── extensions.py        # Flask 확장
│   ├── models/              # 데이터베이스 모델
│   │   ├── __init__.py
│   │   ├── user.py          # 사용자 모델
│   │   └── post.py          # 게시글 모델
│   ├── routes/              # 라우트
│   │   ├── __init__.py
│   │   ├── auth.py          # 인증 라우트
│   │   ├── posts.py         # 게시글 라우트
│   │   └── files.py         # 파일 라우트
│   ├── services/            # 비즈니스 로직
│   │   └── posts_service.py
│   ├── utils/               # 유틸리티
│   │   ├── storage.py       # 파일 저장
│   │   ├── pagination.py    # 페이지네이션
│   │   ├── logging.py       # 로깅
│   │   └── errors.py        # 에러 처리
│   ├── templates/           # HTML 템플릿
│   │   ├── base.html        # 기본 템플릿
│   │   ├── index.html       # 메인 페이지
│   │   ├── auth/            # 인증 템플릿
│   │   ├── posts/           # 게시글 템플릿
│   │   └── errors/          # 에러 페이지
│   ├── static/              # 정적 파일
│   │   ├── css/styles.css   # Tailwind CSS
│   │   └── js/app.js        # JavaScript
│   └── uploads/             # 업로드 파일
├── scripts/
│   └── init_db.py           # 데이터베이스 초기화
├── venv/                    # 가상환경
├── .env                     # 환경 변수
├── .gitignore              # Git 무시 파일
├── requirements.txt         # 패키지 목록
├── wsgi.py                 # WSGI 진입점
└── README.md               # 프로젝트 문서
```

## 🛠️ 기술 스택

### 백엔드
- **Flask 3.0+**: 웹 프레임워크
- **SQLAlchemy**: ORM
- **Flask-Login**: 인증 관리
- **Flask-Migrate**: 데이터베이스 마이그레이션
- **Flask-Caching**: 캐싱

### 프론트엔드
- **Tailwind CSS**: 스타일링
- **JavaScript**: 인터랙션

### 데이터베이스
- **PostgreSQL**: 고성능 관계형 DB
- **MySQL**: 인기 있는 오픈소스 DB
- **SQL Server**: Microsoft 엔터프라이즈 DB
- **SQLite**: 경량 파일 기반 DB

## 📦 설치된 패키지

```txt
Flask>=3.0
python-dotenv>=1.0
Flask-SQLAlchemy>=3.0
Flask-Migrate>=4.0
Flask-Login>=0.6
Flask-Caching>=2.0
Werkzeug>=3.0
# + 선택한 데이터베이스 드라이버
```

## 🎯 생성된 앱의 주요 기능

### 인증 시스템
- 로그인/로그아웃
- 세션 관리
- 보안된 라우트 보호

### 게시판 시스템
- 게시글 목록 보기
- 게시글 상세 보기
- 새 게시글 작성
- 게시글 수정/삭제
- 페이지네이션

### 파일 관리
- 파일 업로드
- 파일 다운로드
- 안전한 파일 저장

## 🔧 개발 환경 설정

생성된 프로젝트에서:

```bash
# 가상환경 활성화
# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

# Flask 앱 실행
flask run
```

## 🔑 기본 계정

- **사용자명**: `admin`
- **비밀번호**: `admin123`

## 🏗️ 프로젝트 구조 (Builder)

```
flask_builder/
├── main.py                 # 메인 실행 파일
├── config.py              # 설정 상수
├── utils/                 # 유틸리티
│   ├── __init__.py
│   └── helpers.py         # 헬퍼 함수들
├── builders/              # 빌더 클래스들
│   ├── __init__.py
│   ├── database_builder.py # DB 설정 빌더
│   └── project_builder.py  # 프로젝트 구조 빌더
└── templates/             # 템플릿 파일들
    ├── __init__.py
    ├── gitignore.py       # .gitignore 템플릿
    ├── python_files.py    # Python 파일 템플릿
    ├── config_templates.py # 설정 파일 템플릿
    ├── extensions_templates.py # 확장 템플릿
    ├── models_templates.py # 모델 템플릿
    ├── routes_templates.py # 라우트 템플릿
    ├── services_templates.py # 서비스 템플릿
    ├── utils_templates.py # 유틸리티 템플릿
    ├── html_templates.py  # HTML 템플릿
    ├── auth_templates.py  # 인증 템플릿
    ├── posts_templates.py # 게시글 템플릿
    └── static_files.py    # 정적 파일 템플릿
```

## 🎨 모듈화의 장점

1. **🔧 유지보수성**: 각 기능이 독립적인 모듈로 분리
2. **♻️ 재사용성**: 템플릿과 빌더를 다른 프로젝트에서 재사용
3. **📈 확장성**: 새로운 데이터베이스나 UI 스택 쉽게 추가
4. **🧪 테스트 용이성**: 각 모듈을 독립적으로 테스트
5. **📖 가독성**: 논리적으로 분리된 코드 구조

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.

## 🙏 감사의 말

- [Flask](https://flask.palletsprojects.com/) - 웹 프레임워크
- [Tailwind CSS](https://tailwindcss.com/) - CSS 프레임워크
- [SQLAlchemy](https://www.sqlalchemy.org/) - ORM

## 📞 문의

프로젝트에 대한 질문이나 제안사항이 있으시면 [Issues](https://github.com/yourusername/flask-builder/issues)에 등록해 주세요.

---

⭐ 이 프로젝트가 도움이 되었다면 스타를 눌러주세요!
