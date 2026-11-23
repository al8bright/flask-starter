"""check_common_layer.py 테스트 — 표준 라이브러리 unittest 만 쓴다.

실행: python -B -m unittest discover -s tools
"""

import tempfile
import unittest
from pathlib import Path

import check_common_layer as ccl


def write(root: Path, rel: str, data: bytes) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


class CompareTest(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.here = Path(self._dir.name, "here")
        self.source = Path(self._dir.name, "source")
        self.paths = ("app/core", "alembic.ini")

    def tearDown(self):
        self._dir.cleanup()

    def test_줄바꿈만_다르면_같다(self):
        write(self.here, "app/core/a.py", b"x = 1\r\ny = 2\r\n")
        write(self.source, "app/core/a.py", b"x = 1\ny = 2\n")
        write(self.here, "alembic.ini", b"[alembic]\n")
        write(self.source, "alembic.ini", b"[alembic]\n")
        self.assertEqual(
            ccl.compare(self.here, self.source, self.paths), {"different": [], "only_here": [], "only_source": []}
        )

    def test_내용_차이와_한쪽에만_있는_파일을_나눈다(self):
        write(self.here, "app/core/a.py", b"x = 1\n")
        write(self.source, "app/core/a.py", b"x = 2\n")
        write(self.here, "app/core/mine.py", b"")
        write(self.source, "app/core/new.py", b"")
        write(self.source, "alembic.ini", b"[alembic]\n")
        self.assertEqual(
            ccl.compare(self.here, self.source, self.paths),
            # 결과는 검사 경로(paths) 순서를 따른다 — app/core 다음 alembic.ini
            {
                "different": ["app/core/a.py"],
                "only_here": ["app/core/mine.py"],
                "only_source": ["app/core/new.py", "alembic.ini"],
            },
        )

    def test_캐시_폴더는_비교하지_않는다(self):
        write(self.here, "app/core/__pycache__/a.cpython-313.pyc", b"\x00")
        self.assertEqual(ccl.list_files(self.here, "app/core"), set())


class MainTest(unittest.TestCase):
    def test_원본이_없으면_종료_코드_2(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(ccl.main(["--source", str(Path(d, "없는저장소"))]), 2)


if __name__ == "__main__":
    unittest.main()
