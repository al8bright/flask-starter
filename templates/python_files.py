"""
Python 파일 템플릿들
"""
from textwrap import dedent

APP_INIT = dedent("""
    import os
    from flask import Flask, render_template, request, session
    from dotenv import load_dotenv
    
    from app.config import config
    from app.extensions import init_extensions
    from app.utils.logging import setup_logging
    from app.utils.errors import register_error_handlers
    
    def create_app(config_name=None):
        '''애플리케이션 팩토리'''
        load_dotenv()
        
        app = Flask(__name__)
        
        # 설정 로드
        if config_name is None:
            config_name = os.environ.get('FLASK_ENV', 'development')
        app.config.from_object(config[config_name])
        
        # 확장 초기화
        init_extensions(app)
        
        # 로깅 설정
        setup_logging(app)
        
        # 에러 핸들러 등록
        register_error_handlers(app)
        
        # 블루프린트 등록
        from app.routes import init_app as init_routes
        init_routes(app)
        
        # Jinja2 필터 추가
        @app.template_filter('nl2br')
        def nl2br_filter(text):
            '''줄바꿈을 <br> 태그로 변환'''
            if text:
                return text.replace('\\n', '<br>')
            return text
        
        return app

    # WSGI entrypoint
    app = create_app()
""")

WSGI = dedent("""
    from app import app

    if __name__ == '__main__':
        app.run(debug=True)
""")

ROUTES = dedent("""
    # Optional blueprint file if you want to expand routes later.
    from flask import Blueprint, render_template

    bp = Blueprint('main', __name__)

    @bp.route('/hello')
    def hello():
        return render_template('index.html', title='Hello')
""")

INIT_DB = dedent("""
    # scripts/init_db.py
    import os
    import subprocess
    import sys
    from app import create_app
    from app.extensions import db, migrate
    from app.models.user import User
    from app.models.post import Post

    def init_db():
        '''데이터베이스 초기화 및 기본 데이터 생성'''
        app = create_app()
        
        with app.app_context():
            # 0. 기존 테이블 완전 제거
            print("기존 테이블 정리 중...")
            try:
                from sqlalchemy import text, inspect
                
                # 데이터베이스 엔진에서 모든 테이블 정보 가져오기
                inspector = inspect(db.engine)
                all_tables = inspector.get_table_names()
                
                if all_tables:
                    print(f"발견된 테이블: {', '.join(all_tables)}")
                    
                    # 모든 테이블 삭제 (CASCADE로 의존성 있는 테이블도 함께 삭제)
                    for table_name in all_tables:
                        db.session.execute(text(f"DROP TABLE IF EXISTS {table_name} CASCADE"))
                    
                    db.session.commit()
                    print(f"[SUCCESS] {len(all_tables)}개 테이블 제거 완료")
                else:
                    print("[INFO] 삭제할 테이블이 없습니다")
                    
            except Exception as e:
                print(f"[WARN] 기존 테이블 제거 실패: {e}")
                db.session.rollback()
            
            # 1. Flask-Migrate 초기화 (migrations 폴더가 없을 경우)
            if not os.path.exists('migrations'):
                print("Flask-Migrate 초기화 중...")
                try:
                    if os.name == "nt":
                        subprocess.run([sys.executable, '-m', 'flask', 'db', 'init'], 
                                     check=True, capture_output=True, text=True)
                    else:
                        subprocess.run([sys.executable, '-m', 'flask', 'db', 'init'], 
                                     check=True, capture_output=True, text=True, encoding='utf-8')
                    print("[SUCCESS] Flask-Migrate 초기화 완료")
                except subprocess.CalledProcessError as e:
                    print(f"[WARN] Flask-Migrate 초기화 실패: {e}")
            
            # 2. 마이그레이션 파일 생성
            print("마이그레이션 파일 생성 중...")
            try:
                if os.name == "nt":
                    subprocess.run([sys.executable, '-m', 'flask', 'db', 'migrate', '-m', 'Initial migration'], 
                                 check=True, capture_output=True, text=True)
                else:
                    subprocess.run([sys.executable, '-m', 'flask', 'db', 'migrate', '-m', 'Initial migration'], 
                                 check=True, capture_output=True, text=True, encoding='utf-8')
                print("[SUCCESS] 마이그레이션 파일 생성 완료")
            except subprocess.CalledProcessError as e:
                print(f"[WARN] 마이그레이션 파일 생성 실패: {e}")
            
            # 3. 마이그레이션 적용
            print("마이그레이션 적용 중...")
            try:
                if os.name == "nt":
                    subprocess.run([sys.executable, '-m', 'flask', 'db', 'upgrade'], 
                                 check=True, capture_output=True, text=True)
                else:
                    subprocess.run([sys.executable, '-m', 'flask', 'db', 'upgrade'], 
                                 check=True, capture_output=True, text=True, encoding='utf-8')
                print("[SUCCESS] 마이그레이션 적용 완료")
                
                # 마이그레이션 후 테이블 존재 확인
                result = db.session.execute(text("SELECT COUNT(*) FROM users"))
                print("[SUCCESS] 테이블 확인 완료")
                
            except subprocess.CalledProcessError as e:
                print(f"[WARN] 마이그레이션 적용 실패: {e}")
                # 마이그레이션 실패 시 fallback으로 create_all 사용
                print("Fallback: db.create_all() 사용")
                db.create_all()
            except Exception as e:
                print(f"[WARN] 테이블 확인 실패: {e}")
                # 테이블이 없으면 create_all 사용
                print("Fallback: db.create_all() 사용")
                db.create_all()
            
            # 4. 기본 사용자 생성
            if not User.query.filter_by(username='admin').first():
                admin_user = User(
                    username='admin',
                    email='admin@example.com'
                )
                admin_user.set_password('admin123')
                db.session.add(admin_user)
                db.session.commit()
                print("[SUCCESS] 기본 사용자 생성 완료:")
                print("  사용자명: admin")
                print("  비밀번호: admin123")
            
            # 5. 샘플 게시글 생성
            if not Post.query.first():
                admin_user = User.query.filter_by(username='admin').first()
                sample_post = Post(
                    title='환영합니다!',
                    content='Flask 게시판 애플리케이션에 오신 것을 환영합니다.\\n\\n이 애플리케이션은 다음과 같은 기능을 제공합니다:\\n\\n- 사용자 인증 (로그인/로그아웃)\\n- 게시글 CRUD (생성/조회/수정/삭제)\\n- 파일 업로드 및 다운로드\\n- Tailwind CSS UI\\n- Flask-Caching\\n\\n새로운 게시글을 작성해보세요!',
                    user_id=admin_user.id
                )
                db.session.add(sample_post)
                db.session.commit()
                print("[SUCCESS] 샘플 게시글 생성 완료")
            
            print("[SUCCESS] 데이터베이스 초기화가 완료되었습니다.")

    if __name__ == '__main__':
        init_db()
""")
