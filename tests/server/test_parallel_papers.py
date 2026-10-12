import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from easyread.library.library import Library
from easyread.library.store import Workspace, write_json_atomic
from easyread.server.jobs import Jobs


class ParallelPapersTest(unittest.TestCase):
    def test_two_papers_are_translated_at_the_same_time(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        lib = Library(Path(tmp.name))
        wss = []
        for name in ("paper0001", "paper0002"):
            root = lib.root / name
            root.mkdir()
            ws = Workspace(root)
            write_json_atomic(ws.paper_path, {"meta": {"pages": [{"n": 1}], "page_count": 1}})
            wss.append(ws)
        both = threading.Barrier(2, timeout=5)  # 两篇都进了翻译才放行；如果串行，第一篇会等超时

        def run(jobs, ws, job, cancel):
            both.wait()
            jobs._write(ws, state="done")

        with patch.object(Jobs, "_run_bulk", run):
            jobs = Jobs(lib)
            for ws in wss:
                jobs.enqueue(ws, pages=[1])
            deadline = time.time() + 10
            while time.time() < deadline and not all(ws.load("job")["state"] == "done" for ws in wss):
                time.sleep(0.05)
        for ws in wss:
            self.assertEqual(ws.load("job")["state"], "done")


if __name__ == "__main__":
    unittest.main()
