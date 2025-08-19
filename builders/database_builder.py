"""
데이터베이스 설정 빌더
"""
from utils.helpers import ask, ask_secret, choose


class DatabaseBuilder:
    """데이터베이스 설정을 담당하는 클래스"""
    
    def __init__(self):
        self.db_url = ""
        self.driver_packages = []
    
    def configure(self) -> tuple[str, list[str]]:
        """데이터베이스 설정을 구성하고 URL과 드라이버 패키지 목록을 반환"""
        db_choice = choose(
            "데이터베이스를 선택하세요:", ["PostgreSQL", "MySQL", "SQL Server", "건너뛰기"], 0
        )
        
        if db_choice == "건너뛰기":
            return "", []
        
        if db_choice == "PostgreSQL":
            return self._configure_postgresql()
        elif db_choice == "MySQL":
            return self._configure_mysql()
        elif db_choice == "SQL Server":
            return self._configure_sqlserver()
        
        return "", []
    
    def _configure_postgresql(self) -> tuple[str, list[str]]:
        """PostgreSQL 설정"""
        host = ask("DB 호스트", "127.0.0.1")
        port = ask("DB 포트", "5432")
        db = ask("DB 이름", "my_flask_app")
        user = ask("DB 사용자", "postgres")
        pw = ask_secret("DB 비밀번호")
        
        db_url = f"postgresql+psycopg://{user}:{pw}@{host}:{port}/{db}"
        driver_packages = ["psycopg[binary]"]
        
        return db_url, driver_packages
    
    def _configure_mysql(self) -> tuple[str, list[str]]:
        """MySQL 설정"""
        host = ask("DB 호스트", "127.0.0.1")
        port = ask("DB 포트", "3306")
        db = ask("DB 이름", "my_flask_app")
        user = ask("DB 사용자", "root")
        pw = ask_secret("DB 비밀번호")
        
        db_url = f"mysql+pymysql://{user}:{pw}@{host}:{port}/{db}"
        driver_packages = ["PyMySQL"]
        
        return db_url, driver_packages
    
    def _configure_sqlserver(self) -> tuple[str, list[str]]:
        """SQL Server 설정"""
        host = ask("DB 호스트", "127.0.0.1")
        port = ask("DB 포트", "1433")
        db = ask("DB 이름", "my_flask_app")
        user = ask("DB 사용자", "sa")
        pw = ask_secret("DB 비밀번호")
        driver = ask("ODBC 드라이버 이름", "ODBC Driver 18 for SQL Server")
        
        # Note: URL must percent-encode spaces in driver name as +, SQLAlchemy handles if spaces replaced by +
        driver_encoded = driver.replace(" ", "+")
        db_url = f"mssql+pyodbc://{user}:{pw}@{host},{port}/{db}?driver={driver_encoded}"
        driver_packages = ["pyodbc"]
        
        return db_url, driver_packages


