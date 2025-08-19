#!/usr/bin/env python3
"""
main.py — Flask 프로젝트 스캐폴더 메인 실행 파일

Usage:
    python main.py

What it does (interactively):
  1) Ask for project name.
  2) Ask for DB engine (PostgreSQL / MySQL / SQL Server) and connection details.
  3) Create project structure with templates/static (Tailwind CSS).
  4) Create a Python venv in ./venv and install requirements.
  5) Write .env with DATABASE_URL & SECRET_KEY.
  6) Create a sample table via SQLAlchemy Core (users).

Tested on: macOS/Linux/Windows (requires internet for pip installs; SQL Server needs ODBC driver installed).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from utils.helpers import ask, warn, err
from builders.database_builder import DatabaseBuilder
from builders.project_builder import ProjectBuilder


def main() -> None:
    """메인 실행 함수"""
    print("\n=== Flask App Builder ===\n")
    
    # 프로젝트 이름 입력
    project_name = ask("프로젝트 이름", "my_flask_app")
    
    # 프로젝트 경로 입력
    project_path = ask("프로젝트 생성 경로 (예: P:\\flask)", str(Path.cwd().parent))
    
    # 데이터베이스 설정
    db_builder = DatabaseBuilder()
    db_url, driver_packages = db_builder.configure()
    
    # 프로젝트 빌드
    project_builder = ProjectBuilder(project_name, db_url, driver_packages, project_path)
    project_builder.build()
    
    # SQL Server 특별 안내
    if "pyodbc" in driver_packages:
        warn("Windows 이외 환경에서는 ODBC 드라이버(17/18) 설치가 추가로 필요합니다.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        err("사용자 취소")
        sys.exit(130)
