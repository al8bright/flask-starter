"""check_projects.py 테스트 — 표준 라이브러리 unittest 만 쓴다(템플릿 저장소에 설치하지 않기 위해).

실행: python -B -m unittest discover -s tools
"""

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import check_projects as cp


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="")


class ParseRequirementsTest(unittest.TestCase):
    def test_정확_핀과_extras_대소문자를_정규화한다(self):
        text = "# 주석\nFlask==3.1.3\nuvicorn[standard]==0.54.0\nPyJWT==2.15.1  # 서명\n\n-r other.txt\n"
        self.assertEqual(
            cp.parse_requirements(text),
            {"flask": "3.1.3", "uvicorn": "0.54.0", "pyjwt": "2.15.1"},
        )

    def test_환경_마커는_떼고_버전만_남긴다(self):
        self.assertEqual(cp.parse_requirements('gunicorn==27.0.1; sys_platform != "win32"\n'), {"gunicorn": "27.0.1"})

    def test_정확_핀이_아니면_조건식을_그대로_남긴다(self):
        self.assertEqual(cp.parse_requirements("httpx2>=2.13,<3\n"), {"httpx2": ">=2.13,<3"})

    def test_밑줄과_점은_하이픈으로_본다(self):
        self.assertEqual(cp.parse_requirements("pydantic_settings==2.16.2\n"), {"pydantic-settings": "2.16.2"})


class ParseVersionsEnvTest(unittest.TestCase):
    def test_주석을_건너뛰고_따옴표를_벗긴다(self):
        text = '# 하한\nMIN_PYTHON=3.13\nTAILWIND_VERSION="4.3.5"\n\nHTMX_VERSION=2.0.11\n'
        self.assertEqual(
            cp.parse_versions_env(text),
            {"MIN_PYTHON": "3.13", "TAILWIND_VERSION": "4.3.5", "HTMX_VERSION": "2.0.11"},
        )


class HtmxVersionTest(unittest.TestCase):
    def test_벤더링_파일의_version_문자열을_읽는다(self):
        self.assertEqual(cp.htmx_version('var htmx=function(){return{config:{},version:"2.0.11"}}()'), "2.0.11")

    def test_없으면_빈_문자열이다(self):
        self.assertEqual(cp.htmx_version(""), "")


class ProjectNamesTest(unittest.TestCase):
    def test_치환된_표시_이름과_snake_이름을_읽는다(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d, "folder")
            write(root, "app/main.py", 'import x\nPROJECT_NAME = "Demo App"\n')
            write(root, "app/dependencies.py", 'AUTH_COOKIE = "demo_app_session"\n')
            self.assertEqual(cp.project_names(root), cp.ProjectNames("Demo App", "demo_app"))

    def test_찾지_못하면_폴더_이름을_쓴다(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(cp.project_names(Path(d, "chimmelier")), cp.ProjectNames("chimmelier", "chimmelier"))


class DiffTest(unittest.TestCase):
    def test_줄바꿈만_다르면_차이가_없다(self):
        self.assertEqual(cp.diff_line_count("a\r\nb\r\n", "a\nb\n"), 0)

    def test_바뀐_줄은_지운_줄과_더한_줄로_센다(self):
        self.assertEqual(cp.diff_line_count("a\nb\nc\n", "a\nB\nc\n"), 2)

    def test_두_토큰을_각각의_값으로_바꾼다(self):
        names = cp.ProjectNames("Demo App", "demo_app")
        self.assertEqual(
            cp.substitute_tokens('"__PROJECT_SNAKE___session" / __PROJECT_NAME__', names),
            '"demo_app_session" / Demo App',
        )


class CompareFilesTest(unittest.TestCase):
    def test_같음_다름_없음으로_나누고_산출물은_뺀다(self):
        with tempfile.TemporaryDirectory() as d:
            skel, proj = Path(d, "skeleton"), Path(d, "proj")
            files = {
                "same.txt": ("x\n", "x\r\n"),
                "token.txt": ("__PROJECT_SNAKE__ / __PROJECT_NAME__\n", "demo / Demo\n"),
                "diff.txt": ("a\n", "b\n"),
                "missing.txt": ("a\n", None),
                ".env": ("A=1\n", "A=2\n"),
                ".venv/x.py": ("a\n", "b\n"),
                "app/static/css/app.css": ("a\n", "b\n"),
            }
            for rel, (s, p) in files.items():
                write(skel, rel, s)
                if p is not None:
                    write(proj, rel, p)
            result = cp.compare_files(skel, proj, cp.ProjectNames("Demo", "demo"))
        self.assertEqual(result.same, ["same.txt", "token.txt"])
        self.assertEqual(result.different, {"diff.txt": 2})
        self.assertEqual(result.missing, ["missing.txt"])


class FileGroupTest(unittest.TestCase):
    def test_화면_템플릿과_프로젝트_문서는_공통_인프라가_아니다(self):
        for rel in ["app/templates/base.html", "app/templates/admin/dashboard.html", "README.md", "PLAN.md"]:
            self.assertFalse(cp.is_infra_file(rel), rel)

    def test_스킬_스크립트_CI_앱_코드_설정은_공통_인프라다(self):
        for rel in [
            ".claude/skills/pr-workflow/SKILL.md",
            "scripts/tailwind.sh",
            ".github/workflows/ci.yml",
            "app/core/security.py",
            "app/web/htmx.py",
            "app/static/js/app.js",
            "AGENTS.md",
        ]:
            self.assertTrue(cp.is_infra_file(rel), rel)


class MainOutputTest(unittest.TestCase):
    def test_파일로_저장할_때도_안내_문구가_UTF8_로_나간다(self):
        buffer = io.TextIOWrapper(io.BytesIO(), encoding="cp949")
        with tempfile.TemporaryDirectory() as d, redirect_stdout(buffer):
            project = Path(d, "proj")
            project.mkdir()
            cp.main([str(project), "--output", str(Path(d, "out.md"))])
            buffer.flush()
            self.assertEqual(buffer.encoding.lower().replace("-", ""), "utf8")

    def test_스타터를_자기_자신과_비교하면_토큰_파일만_다르다(self):
        # 스타터 skeleton/ 을 프로젝트로 넘기면 토큰이 치환되지 않은 채 남아 있으므로 토큰이 든 파일만 다르게 나온다.
        report, findings = cp.build_report([cp.SKELETON], audit=False, list_files=False)
        self.assertEqual(findings, 0)
        self.assertIn("## 1. 런타임·도구", report)
        self.assertIn("| htmx.min.js |", report)


class VersionTableTest(unittest.TestCase):
    def test_두_곳_이상에_있고_값이_다를_때만_차이로_표시한다(self):
        columns = {
            "스타터": {"flask": "3.1.3", "pyjwt": "2.15.1"},
            "demo": {"flask": "3.1.2", "pyjwt": "2.15.1", "nh3": "0.3.6"},
        }
        self.assertEqual(
            cp.version_rows(columns),
            [
                ["flask", "3.1.3", "3.1.2", "≠"],
                ["nh3", "-", "0.3.6", ""],
                ["pyjwt", "2.15.1", "2.15.1", ""],
            ],
        )


class MarkdownTableTest(unittest.TestCase):
    def test_세로막대를_이스케이프한다(self):
        self.assertEqual(
            cp.markdown_table(["이름", "값"], [["a|b", "1"]]),
            "| 이름 | 값 |\n|---|---|\n| a\\|b | 1 |",
        )


class AuditSummaryTest(unittest.TestCase):
    def test_osv_결과를_패키지별_식별자로_묶는다(self):
        packages = [("pyjwt", "2.13.0"), ("flask", "3.1.3")]
        response = {"results": [{"vulns": [{"id": "GHSA-aaaa"}, {"id": "PYSEC-1"}]}, {}]}
        self.assertEqual(cp.summarize_osv(packages, response), ["pyjwt 2.13.0 — GHSA-aaaa, PYSEC-1"])

    def test_requirements_핀은_정확_버전만_감사_대상이다(self):
        with tempfile.TemporaryDirectory() as d:
            text = 'flask==3.1.3\nhttpx2>=2.13\ngunicorn==27.0.1; sys_platform != "win32"\n'
            write(Path(d), "requirements.txt", text)
            packages, source = cp.python_packages(Path(d))
        self.assertEqual(packages, [("flask", "3.1.3"), ("gunicorn", "27.0.1")])
        self.assertEqual(source, "requirements 핀")


class ProjectPathsTest(unittest.TestCase):
    def test_인자가_있으면_인자를_쓴다(self):
        self.assertEqual(cp.resolve_project_paths(["../a"], Path("없는파일.txt")), [Path("../a")])

    def test_인자가_없으면_로컬_목록_파일을_읽는다(self):
        with tempfile.TemporaryDirectory() as d:
            listing = Path(d, "projects.local.txt")
            listing.write_text("# 내 프로젝트\nC:/Personal/a\n\nC:/Personal/b\n", encoding="utf-8")
            self.assertEqual(cp.resolve_project_paths([], listing), [Path("C:/Personal/a"), Path("C:/Personal/b")])

    def test_둘_다_없으면_안내와_함께_실패한다(self):
        with self.assertRaises(SystemExit) as ctx:
            cp.resolve_project_paths([], Path("없는파일"))
        self.assertIn("projects.local.txt", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
