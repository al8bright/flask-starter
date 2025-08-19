"""
Flask 확장 템플릿들
"""
from textwrap import dedent

EXTENSIONS_PY = dedent("""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_caching import Cache
from flask_login import LoginManager
from flask_babel import Babel


# 데이터베이스
db = SQLAlchemy()

# 마이그레이션
migrate = Migrate()

# 캐싱
cache = Cache()

# 로그인 관리
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = '이 페이지에 접근하려면 로그인이 필요합니다.'
login_manager.login_message_category = 'info'

# 다국어 지원
babel = Babel()


def init_extensions(app):
    '''Flask 확장들을 초기화합니다'''
    db.init_app(app)
    migrate.init_app(app, db)
    cache.init_app(app)
    login_manager.init_app(app)
    
    # Babel 로케일 선택자
    def get_locale():
        from flask import request, session
        # 세션에서 언어 설정 확인
        if 'locale' in session:
            return session['locale']
        # 브라우저 언어 설정 확인
        return request.accept_languages.best_match(['ko', 'en'])
    
    babel.init_app(app, locale_selector=get_locale)
    
    # Babel 번역 파일 컴파일
    try:
        import subprocess
        import os
        subprocess.run(['pybabel', 'compile', '-d', 'babel/locale'], 
                      cwd=os.getcwd(), capture_output=True)
    except:
        pass  # pybabel이 없거나 컴파일 실패해도 계속 진행
    
    # 사용자 로더 설정
    from app.models.user import User
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
""")
