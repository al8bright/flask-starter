"""
Git 관련 템플릿
"""
from textwrap import dedent

GITIGNORE = dedent(
    """
    # Python
    __pycache__/
    *.py[cod]
    *.pyo
    *.pyd
    .Python
    build/
    develop-eggs/
    dist/
    downloads/
    eggs/
    .eggs/
    lib/
    lib64/
    parts/
    sdist/
    var/
    wheels/
    *.egg-info/
    .installed.cfg
    *.egg

    # Virtual env
    venv/
    .venv/

    # dotenv
    .env

    # IDE
    .vscode/
    .idea/
    """
)
