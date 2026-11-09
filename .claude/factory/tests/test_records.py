"""The record files' one reader and their shapes.

Lacks: records from a real build; the writers' output is checked in test_ready, test_checks, test_ledger and test_github.

Run: python3 -B -m unittest discover -s kit/_claude/factory/tests
"""
import json
import os
import unittest

from fixtures import Repo


def jsonl(*records):
    return "".join(json.dumps(r) + "\n" for r in records)


class Records(unittest.TestCase):
    def test_the_shared_reader_skips_a_line_of_the_wrong_type_in_any_record_file(self):
        """read_records skips a flakes line with a list title and a line that is an array, in every reader of the file"""
        import tempfile
        from gate.records import read_records
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "flakes.jsonl")
            with open(path, "w") as handle:
                handle.write(jsonl({"title": "ok", "file": "f"}, {"title": ["a"], "file": "f"}) + "[1]\n")
            records, skipped = read_records(path)
        self.assertEqual(([r["title"] for r in records], skipped), (["ok"], 2))

    def test_sample_previews_the_page_though_factory_json_is_invalid(self):
        """dashboard --sample writes the page when factory.json is invalid"""
        repo = Repo()
        repo.write("docs/agents/local/factory.json", json.dumps({"prices": {"m": {"input": "3"}}}))
        out_path = os.path.join(repo.root, "s.html")
        code, out = repo.gate("dashboard", out_path, "--sample")
        self.assertEqual(code, 0, out)
        self.assertTrue(os.path.exists(out_path))
