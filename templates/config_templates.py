"""
환경별 설정 템플릿들
"""
from textwrap import dedent

CONFIG_PY = dedent("""
    import os
    from datetime import timedelta
    
    
    class Config:
        '''기본 설정 클래스'''
        SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
        SQLALCHEMY_TRACK_MODIFICATIONS = False
        SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///app.db'
        
        # 파일 업로드 설정
        UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
        MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
        ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx'}
        
        # 캐싱 설정
        CACHE_TYPE = "SimpleCache"
        CACHE_DEFAULT_TIMEOUT = 300
        
        # 세션 설정
        PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
        
        # 페이지네이션
        POSTS_PER_PAGE = 10
    
    
    class DevelopmentConfig(Config):
        '''개발 환경 설정'''
        DEBUG = True
        SQLALCHEMY_ECHO = True
    
    
    class TestingConfig(Config):
        '''테스트 환경 설정'''
        TESTING = True
        SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
        WTF_CSRF_ENABLED = False
    
    
    class ProductionConfig(Config):
        '''프로덕션 환경 설정'''
        DEBUG = False
        SQLALCHEMY_ECHO = False
        
        # 프로덕션에서는 Redis 캐시 사용 권장
        # CACHE_TYPE = "RedisCache"
        # CACHE_REDIS_URL = os.environ.get('REDIS_URL')
        
        # 보안 강화
        SESSION_COOKIE_SECURE = True
        SESSION_COOKIE_HTTPONLY = True
        SESSION_COOKIE_SAMESITE = 'Lax'
    
    
    config = {
        'development': DevelopmentConfig,
        'testing': TestingConfig,
        'production': ProductionConfig,
        'default': DevelopmentConfig
    }
""")
