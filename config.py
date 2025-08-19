"""
설정 관련 상수들
"""

# 기본 패키지 목록
DEFAULT_PACKAGES = [
    "Flask>=3.0",
    "python-dotenv>=1.0", 
    "SQLAlchemy>=2.0",
]

# 데이터베이스 드라이버 매핑
DB_DRIVERS = {
    "PostgreSQL": "psycopg[binary]",
    "MySQL": "PyMySQL", 
    "SQL Server": "pyodbc"
}

# UI 스택 (Tailwind CSS 고정)
UI_STACK = "Tailwind"

# 데이터베이스 옵션
DB_OPTIONS = ["PostgreSQL", "MySQL", "SQL Server", "건너뛰기"]

# 기본 환경 변수
DEFAULT_ENV_VARS = [
    "FLASK_APP=wsgi",
    "FLASK_ENV=development",
]
