#!/usr/bin/env python3
"""
main.py — Flask 프로젝트 스캐폴더 메인 실행 파일

Usage:
    python main.py                    # 대화형 모드
    python main.py --gui             # GUI 모드 (Electron에서 호출)
    python main.py --config <json>   # 설정 파일 모드

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
import json
import argparse
from pathlib import Path

from utils.helpers import ask, warn, err, info
from builders.database_builder import DatabaseBuilder
from builders.project_builder import ProjectBuilder


def parse_gui_config(config_json: str) -> dict:
    """GUI에서 전달받은 JSON 설정을 파싱합니다."""
    try:
        config = json.loads(config_json)
        return {
            'project_name': config.get('projectName', 'my_flask_app'),
            'project_path': config.get('projectPath', ''),
            'database_type': config.get('databaseType', 'sqlite'),
            'database_config': config.get('databaseConfig', {})
        }
    except json.JSONDecodeError as e:
        err(f"설정 파싱 오류: {e}")
        sys.exit(1)


def build_from_gui_config(config: dict) -> None:
    """GUI 설정으로부터 프로젝트를 빌드합니다."""
    project_name = config['project_name']
    project_path = config['project_path']
    database_type = config['database_type']
    database_config = config['database_config']
    
    info(f"프로젝트 생성 시작: {project_name}")
    info(f"생성 경로: {project_path}")
    info(f"데이터베이스: {database_type}")
    
    # 데이터베이스 URL 생성
    db_builder = DatabaseBuilder()
    db_url, driver_packages = db_builder.create_url_from_config(database_type, database_config)
    
    # 프로젝트 빌드
    project_builder = ProjectBuilder(project_name, db_url, driver_packages, project_path)
    project_builder.build()
    
    info("✅ 프로젝트 생성 완료!")


def main() -> None:
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description='Flask 프로젝트 스캐폴더')
    parser.add_argument('--gui', action='store_true', help='GUI 모드로 실행')
    parser.add_argument('--config', type=str, help='JSON 설정 문자열')
    
    args = parser.parse_args()
    
    if args.gui or args.config:
        # GUI 모드
        if args.config:
            config = parse_gui_config(args.config)
        else:
            # stdin에서 JSON 읽기
            config_json = sys.stdin.read().strip()
            config = parse_gui_config(config_json)
        
        build_from_gui_config(config)
    else:
        # 대화형 모드
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
