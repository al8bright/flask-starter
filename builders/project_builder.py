"""
프로젝트 구조 빌더
"""
import os
import secrets
import subprocess
import sys
from pathlib import Path

from utils.helpers import info, warn, ask, choose
from templates.gitignore import GITIGNORE
from templates.python_files import APP_INIT, WSGI, INIT_DB
from templates.config_templates import CONFIG_PY
from templates.extensions_templates import EXTENSIONS_PY
from templates.models_templates import MODELS_INIT, USER_MODEL, POST_MODEL
from templates.utils_templates import STORAGE_UTILS, PAGINATION_UTILS, LOGGING_UTILS, ERRORS_UTILS
from templates.services_templates import POSTS_SERVICE
from templates.routes_templates import ROUTES_INIT, AUTH_ROUTES, POSTS_ROUTES, FILES_ROUTES, MAIN_ROUTES
from templates.html_templates import BASE_TAILWIND, INDEX_HTML, FLASH_MESSAGES_HTML
from templates.auth_templates import LOGIN_HTML
from templates.posts_templates import POSTS_LIST_HTML, POSTS_DETAIL_HTML, POSTS_FORM_HTML
from templates.static_files import STYLES_CSS, APP_JS, README


class ProjectBuilder:
    """Flask 프로젝트 구조를 생성하는 클래스"""
    
    def __init__(self, project_name: str, db_url: str, driver_packages: list[str], project_path: str = None):
        self.project_name = project_name
        self.db_url = db_url
        self.driver_packages = driver_packages
        
        # 프로젝트 경로 설정
        if project_path:
            self.root = Path(project_path) / project_name
        else:
            self.root = Path.cwd() / project_name
    
    def build(self) -> None:
        """프로젝트를 빌드합니다"""
        self._create_project_structure()
        self._write_files()
        self._create_virtual_environment()
        self._setup_database()
        self._show_final_instructions()
    
    def _create_project_structure(self) -> None:
        """프로젝트 디렉토리 구조를 생성합니다"""
        # 프로젝트 상위 디렉토리가 존재하지 않으면 생성
        if not self.root.parent.exists():
            self.root.parent.mkdir(parents=True, exist_ok=True)
            info(f"프로젝트 디렉토리 생성: {self.root.parent}")
        
        if self.root.exists():
            warn(f"{self.root} 이미 존재합니다. 기존 프로젝트를 완전히 제거하고 새로 생성합니다.")
            import shutil
            try:
                shutil.rmtree(self.root)
                print(f"[SUCCESS] 기존 프로젝트 제거 완료: {self.root}")
            except Exception as e:
                warn(f"기존 프로젝트 제거 실패: {e}")
        
        self.root.mkdir(parents=True, exist_ok=True)
        
        # 프로젝트 트리 생성
        app_dir = self.root / "app"
        tpl_dir = app_dir / "templates"
        static_dir = app_dir / "static"
        
        tpl_dir.mkdir(parents=True, exist_ok=True)
        (static_dir / "css").mkdir(parents=True, exist_ok=True)
        (static_dir / "js").mkdir(parents=True, exist_ok=True)
        
        # scripts 디렉토리 생성
        (self.root / "scripts").mkdir(exist_ok=True)
        
        # uploads 디렉토리 생성
        (self.root / "app" / "uploads").mkdir(exist_ok=True)
    
    def _write_files(self) -> None:
        """모든 파일들을 작성합니다"""
        self._write_gitignore()
        self._write_config_files()
        self._write_app_files()
        self._write_models()
        self._write_utils()
        self._write_services()
        self._write_routes()
        self._write_templates()
        self._write_static_files()
        self._write_env_file()
        self._write_requirements()
        self._write_readme()
        self._write_scripts()
    
    def _write_gitignore(self) -> None:
        """Gitignore 파일 작성"""
        (self.root / ".gitignore").write_text(GITIGNORE, encoding="utf-8")
    
    def _write_config_files(self) -> None:
        """설정 파일들 작성"""
        (self.root / "app" / "config.py").write_text(CONFIG_PY, encoding="utf-8")
    
    def _write_app_files(self) -> None:
        """앱 기본 파일들 작성"""
        app_init = APP_INIT.replace("__PROJECT_NAME__", self.project_name)
        (self.root / "app" / "__init__.py").write_text(app_init, encoding="utf-8")
        (self.root / "app" / "extensions.py").write_text(EXTENSIONS_PY, encoding="utf-8")
        (self.root / "wsgi.py").write_text(WSGI, encoding="utf-8")
    
    def _write_models(self) -> None:
        """모델 파일들 작성"""
        models_dir = self.root / "app" / "models"
        models_dir.mkdir(parents=True, exist_ok=True)
        
        (models_dir / "__init__.py").write_text(MODELS_INIT, encoding="utf-8")
        (models_dir / "user.py").write_text(USER_MODEL, encoding="utf-8")
        (models_dir / "post.py").write_text(POST_MODEL, encoding="utf-8")
    
    def _write_utils(self) -> None:
        """유틸리티 파일들 작성"""
        utils_dir = self.root / "app" / "utils"
        utils_dir.mkdir(parents=True, exist_ok=True)
        
        (utils_dir / "__init__.py").write_text("# utils 패키지\n", encoding="utf-8")
        (utils_dir / "storage.py").write_text(STORAGE_UTILS, encoding="utf-8")
        (utils_dir / "pagination.py").write_text(PAGINATION_UTILS, encoding="utf-8")
        (utils_dir / "logging.py").write_text(LOGGING_UTILS, encoding="utf-8")
        (utils_dir / "errors.py").write_text(ERRORS_UTILS, encoding="utf-8")
    
    def _write_services(self) -> None:
        """서비스 파일들 작성"""
        services_dir = self.root / "app" / "services"
        services_dir.mkdir(parents=True, exist_ok=True)
        
        (services_dir / "__init__.py").write_text("# services 패키지\n", encoding="utf-8")
        (services_dir / "posts_service.py").write_text(POSTS_SERVICE, encoding="utf-8")
    
    def _write_routes(self) -> None:
        """라우트 파일들 작성"""
        routes_dir = self.root / "app" / "routes"
        routes_dir.mkdir(parents=True, exist_ok=True)
        
        (routes_dir / "__init__.py").write_text(ROUTES_INIT, encoding="utf-8")
        (routes_dir / "auth.py").write_text(AUTH_ROUTES, encoding="utf-8")
        (routes_dir / "posts.py").write_text(POSTS_ROUTES, encoding="utf-8")
        (routes_dir / "files.py").write_text(FILES_ROUTES, encoding="utf-8")
        (routes_dir / "main.py").write_text(MAIN_ROUTES, encoding="utf-8")
    
    def _write_templates(self) -> None:
        """HTML 템플릿 파일들 작성"""
        templates_dir = self.root / "app" / "templates"
        
        # 기본 템플릿
        base_html = BASE_TAILWIND.replace("__PROJECT_NAME__", self.project_name)
        (templates_dir / "base.html").write_text(base_html, encoding="utf-8")
        
        # 메인 페이지
        index_html = INDEX_HTML.replace("__PROJECT_NAME__", self.project_name)
        (templates_dir / "index.html").write_text(index_html, encoding="utf-8")
        
        # 플래시 메시지 템플릿
        (templates_dir / "flash_messages.html").write_text(FLASH_MESSAGES_HTML, encoding="utf-8")
        
        # 인증 템플릿
        auth_dir = templates_dir / "auth"
        auth_dir.mkdir(exist_ok=True)
        (auth_dir / "login.html").write_text(LOGIN_HTML, encoding="utf-8")
        
        # 게시글 템플릿
        posts_dir = templates_dir / "posts"
        posts_dir.mkdir(exist_ok=True)
        (posts_dir / "list.html").write_text(POSTS_LIST_HTML, encoding="utf-8")
        (posts_dir / "detail.html").write_text(POSTS_DETAIL_HTML, encoding="utf-8")
        (posts_dir / "form.html").write_text(POSTS_FORM_HTML, encoding="utf-8")
        
        # 에러 템플릿
        errors_dir = templates_dir / "errors"
        errors_dir.mkdir(exist_ok=True)
        (errors_dir / "404.html").write_text("""{% extends 'base.html' %}
{% block content %}
<div class="text-center py-12">
  <h1 class="text-4xl font-bold text-gray-900 dark:text-white mb-4">404</h1>
  <p class="text-lg text-gray-600 dark:text-gray-400 mb-8">페이지를 찾을 수 없습니다</p>
  <a href="{{ url_for('posts.list') }}" class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">
    홈으로 돌아가기
  </a>
</div>
{% endblock %}""", encoding="utf-8")
        (errors_dir / "500.html").write_text("""{% extends 'base.html' %}
{% block content %}
<div class="text-center py-12">
  <h1 class="text-4xl font-bold text-gray-900 dark:text-white mb-4">500</h1>
  <p class="text-lg text-gray-600 dark:text-gray-400 mb-8">서버 오류</p>
  <a href="{{ url_for('posts.list') }}" class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded">
    홈으로 돌아가기
  </a>
</div>
{% endblock %}""", encoding="utf-8")
    
    def _write_static_files(self) -> None:
        """정적 파일들 작성"""
        static_dir = self.root / "app" / "static"
        (static_dir / "css" / "styles.css").write_text(STYLES_CSS, encoding="utf-8")
        (static_dir / "js" / "app.js").write_text(APP_JS, encoding="utf-8")
    

    
    def _write_env_file(self) -> None:
        """환경 변수 파일 작성"""
        secret = secrets.token_hex(16)
        env_lines = [
            "FLASK_APP=app",
            "FLASK_ENV=development",
            "FLASK_DEBUG=1",
            f"SECRET_KEY={secret}",
        ]
        
        if self.db_url:
            env_lines.append(f"DATABASE_URL={self.db_url}")
        else:
            env_lines.append("DATABASE_URL=sqlite:///app.db")
        
        (self.root / ".env").write_text("\n".join(env_lines) + "\n", encoding="utf-8")
    
    def _write_requirements(self) -> None:
        """requirements.txt 작성"""
        reqs = [
            "Flask>=3.0",
            "python-dotenv>=1.0",
            "Flask-SQLAlchemy>=3.0",
            "Flask-Migrate>=4.0",
            "Flask-Login>=0.6",
            "Flask-Caching>=2.0",
            "Werkzeug>=3.0",
        ]
        reqs.extend(self.driver_packages)
        (self.root / "requirements.txt").write_text("\n".join(reqs) + "\n", encoding="utf-8")
    
    def _write_readme(self) -> None:
        """README.md 작성"""
        readme_content = README.replace("__PROJECT_NAME__", self.project_name)
        (self.root / "README.md").write_text(readme_content, encoding="utf-8")
    
    def _write_scripts(self) -> None:
        """스크립트 파일들 작성"""
        (self.root / "scripts" / "init_db.py").write_text(INIT_DB, encoding="utf-8")
    
    def _create_virtual_environment(self) -> None:
        """가상환경 생성 및 패키지 설치"""
        venv_dir = self.root / "venv"
        info("가상환경(venv) 생성 중…")
        
        # Windows 환경에서는 인코딩을 지정하지 않음 (시스템 기본 사용)
        if os.name == "nt":
            subprocess.check_call([sys.executable, "-m", "venv", str(venv_dir)])
        else:
            subprocess.check_call([sys.executable, "-m", "venv", str(venv_dir)], encoding='utf-8')
        
        pip_path = venv_dir / ("Scripts/pip.exe" if os.name == "nt" else "bin/pip")
        info("패키지 설치 중…")
        if os.name == "nt":
            subprocess.check_call([str(pip_path), "install", "-r", str(self.root / "requirements.txt")])
        else:
            subprocess.check_call([str(pip_path), "install", "-r", str(self.root / "requirements.txt")], encoding='utf-8')
    
    def _setup_database(self) -> None:
        """데이터베이스 설정"""
        info("데이터베이스 연결 테스트 및 초기화...")
        venv_dir = self.root / "venv"
        py_path = venv_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        
        env = os.environ.copy()
        env.update({
            "PYTHONPATH": str(self.root),
            "FLASK_APP": "app",
            "FLASK_ENV": "development"
        })
        if self.db_url:
            env["DATABASE_URL"] = self.db_url
        
        try:
            # 1. 데이터베이스 연결 테스트
            self._test_database_connection(py_path, env)
            
            # 2. 데이터베이스 초기화 스크립트 실행
            if os.name == "nt":
                subprocess.check_call(
                    [str(py_path), str(self.root / "scripts" / "init_db.py")], 
                    cwd=str(self.root), 
                    env=env
                )
            else:
                subprocess.check_call(
                    [str(py_path), str(self.root / "scripts" / "init_db.py")], 
                    cwd=str(self.root), 
                    env=env,
                    encoding='utf-8'
                )
            info("데이터베이스 초기화 완료")
            
        except subprocess.CalledProcessError as e:
            warn(f"데이터베이스 초기화 실패: {e}")
        except Exception as e:
            warn(f"데이터베이스 설정 오류: {e}")
    
    def _test_database_connection(self, py_path, env) -> None:
        """데이터베이스 연결 테스트"""
        test_script = f"""
import sys
import os
sys.path.insert(0, r'{self.root}')

try:
    from app import create_app
    from app.extensions import db
    
    app = create_app()
    with app.app_context():
        # 데이터베이스 연결 테스트
        from sqlalchemy import text
        db.session.execute(text('SELECT 1'))
        print("[SUCCESS] 데이터베이스 연결 성공!")
        
        # 기존 테이블 정리
        print("기존 테이블 정리 중...")
        try:
            from sqlalchemy import inspect
            
            # 데이터베이스 엔진에서 모든 테이블 정보 가져오기
            inspector = inspect(db.engine)
            all_tables = inspector.get_table_names()
            
            if all_tables:
                print("발견된 테이블: " + ", ".join(all_tables))
                
                # 모든 테이블 삭제 (CASCADE로 의존성 있는 테이블도 함께 삭제)
                for table_name in all_tables:
                    db.session.execute(text("DROP TABLE IF EXISTS " + table_name + " CASCADE"))
                
                db.session.commit()
                print("[SUCCESS] " + str(len(all_tables)) + "개 테이블 제거 완료")
            else:
                print("[INFO] 삭제할 테이블이 없습니다")
                
        except Exception as e:
            print(f"[WARN] 기존 테이블 제거 실패: {{e}}")
            db.session.rollback()
        
        # 테이블 생성 테스트
        db.create_all()
        print("[SUCCESS] 테이블 생성 성공!")
        
except Exception as e:
    print(f"[ERROR] 데이터베이스 연결 실패: {{e}}")
    sys.exit(1)
"""
        
        test_file = self.root / "test_db_connection.py"
        test_file.write_text(test_script, encoding="utf-8")
        
        try:
            if os.name == "nt":
                result = subprocess.run(
                    [str(py_path), str(test_file)],
                    cwd=str(self.root),
                    env=env,
                    capture_output=True,
                    text=True
                )
            else:
                result = subprocess.run(
                    [str(py_path), str(test_file)],
                    cwd=str(self.root),
                    env=env,
                    capture_output=True,
                    text=True,
                    encoding='utf-8'
                )
            
            if result.returncode == 0:
                info(result.stdout.strip())
            else:
                error_msg = result.stderr.strip() if result.stderr else "알 수 없는 오류"
                warn(f"데이터베이스 연결 실패: {error_msg}")
                if result.stdout:
                    warn(f"출력: {result.stdout.strip()}")
                raise Exception(f"데이터베이스 연결 실패: {error_msg}")
                
        finally:
            # 테스트 파일 정리
            if test_file.exists():
                test_file.unlink()
    
    def _show_final_instructions(self) -> None:
        """최종 실행 안내"""
        print(f"\n프로젝트 생성 완료:\n   {self.root}")
        print("\n다음 명령으로 시작하세요:")
        
        if os.name == "nt":
            print("   venv\\Scripts\\activate")
            print("   flask run")
        else:
            print("   source venv/bin/activate")
            print("   flask run")
        
        print("\n기본 사용자 정보:")
        print("   사용자명: admin")
        print("   비밀번호: admin123")
        
        print("\n주요 기능:")
        print("   - /auth/login: 로그인")
        print("   - /posts: 게시글 목록")
        print("   - /posts/new: 새 글 작성")
        print("   - 파일 업로드/다운로드 지원")
        print("   - 라이트/다크 모드 토글")
