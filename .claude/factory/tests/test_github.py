"""The github command: the repository's Actions usage and storage, over a stub `gh` on PATH.

No test reaches the network: `gh` is a stub executable answering from a JSON file.
Run: python3 -B -m unittest discover -s kit/_claude/factory/tests
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

# Recorded from the real `gh` (kit-dashboard-review, .scratch/kit-dashboard-review/recorded/): the exact texts.
SIGNED_OUT = "You are not logged into any GitHub hosts. To log in, run: gh auth login\n"
BAD_NETWORK = "github.com\n  X Failed to log in to github.com using token (GH_TOKEN)\n  - Active account: true\n  - The token in GH_TOKEN is invalid.\n"

from fixtures import CLEAN_ENV, GATE, Repo

STUB = """#!%s
import json, os, sys
SIGNED_OUT = %r
cfg = json.load(open(os.environ["GH_STUB"]))
args = sys.argv[1:]
with open(os.environ["GH_STUB"] + ".calls", "a") as log:
    log.write(json.dumps(args) + "\\n")
if args[:2] == ["auth", "status"]:
    import time
    time.sleep(cfg.get("auth_sleep", 0))
    if not cfg.get("signed_in", True):
        sys.stderr.write(cfg.get("auth_text", SIGNED_OUT))
    sys.exit(0 if cfg.get("signed_in", True) else 1)
url = [a for a in args[1:] if a.startswith("/")][0]
for key, value in sorted(cfg["routes"].items(), key=lambda kv: -len(kv[0])):
    if url.startswith(key):
        if isinstance(value, dict) and "error" in value:
            sys.stderr.write(value["error"])
            sys.exit(1)
        print(json.dumps(value))
        sys.exit(0)
sys.stderr.write("gh: Not Found (HTTP 404)")
sys.exit(1)
""" % (sys.executable, SIGNED_OUT)

ITEMS = [
    {"date": "2026-11-03T00:00:00Z", "product": "actions", "sku": "Actions Linux", "quantity": 12.0, "unitType": "Minutes", "pricePerUnit": 0.008, "grossAmount": 0.1, "discountAmount": 0.1, "netAmount": 0.0, "repositoryName": "kit"},
    {"date": "2026-11-03T00:00:00Z", "product": "actions", "sku": "Actions Linux", "quantity": 99.0, "unitType": "Minutes", "pricePerUnit": 0.008, "grossAmount": 0.8, "discountAmount": 0.0, "netAmount": 0.8, "repositoryName": "other"},
    {"date": "2026-11-04T00:00:00Z", "product": "actions", "sku": "Actions Linux", "quantity": 5.0, "unitType": "Minutes", "pricePerUnit": 0.008, "grossAmount": 0.04, "discountAmount": 0.0, "netAmount": 0.04, "repositoryName": "kit"},
]
OCT = [{"date": "2026-10-30T00:00:00Z", "product": "actions", "sku": "Actions Linux", "quantity": 7.0, "unitType": "Minutes", "pricePerUnit": 0.008, "grossAmount": 0.06, "discountAmount": 0.0, "netAmount": 0.06, "repositoryName": "kit"}]


class Github(unittest.TestCase):
    def setUp(self):
        self.repo = Repo()
        self.bin = tempfile.mkdtemp(prefix="gh-stub-")
        self.addCleanup(shutil.rmtree, self.bin, True)
        self.stub = os.path.join(self.bin, "cfg.json")
        with open(os.path.join(self.bin, "gh"), "w") as handle:
            handle.write(STUB)
        os.chmod(os.path.join(self.bin, "gh"), 0o755)
        self.local = os.path.join(self.repo.root, "docs/agents/local")

    def remote(self, url="git@github.com:zak/kit.git"):
        subprocess.run(["git", "-C", self.repo.root, "remote", "add", "origin", url], check=True, capture_output=True, env=CLEAN_ENV)

    def routes(self, billing=None, owner_type="User", signed_in=True, storage=True, owner=True, auth_sleep=0, auth_text=None):
        routes = {"/users/zak": {"type": owner_type}} if owner else {}
        routes["/organizations/zak/settings/billing/usage" if owner_type == "Organization" else "/users/zak/settings/billing/usage"] = billing if billing is not None else {"usageItems": ITEMS}
        if storage:
            routes["/repos/zak/kit/actions/artifacts?per_page=100&page=1"] = {"artifacts": [{"size_in_bytes": 100, "expired": False}, {"size_in_bytes": 50, "expired": False}, {"size_in_bytes": 900, "expired": True}]}
            routes["/repos/zak/kit/actions/cache/usage"] = {"active_caches_size_in_bytes": 4096}
        with open(self.stub, "w") as handle:
            json.dump({"routes": routes, "signed_in": signed_in, "auth_sleep": auth_sleep, **({"auth_text": auth_text} if auth_text is not None else {})}, handle)

    def gate(self, *args, path=None, extra=None):
        env = dict(CLEAN_ENV, GH_STUB=self.stub, PATH=path if path is not None else self.bin + os.pathsep + CLEAN_ENV["PATH"], **(extra or {}))
        result = subprocess.run([sys.executable, GATE, "github"] + list(args), cwd=self.repo.root, capture_output=True, text=True, env=env)
        return result.returncode, result.stdout + result.stderr

    def lines(self):
        with open(os.path.join(self.local, "github.jsonl")) as handle:
            return [json.loads(line) for line in handle if line.strip()]

    def calls(self):
        with open(self.stub + ".calls") as handle:
            return [json.loads(line) for line in handle]

    def test_github_writes_only_this_repositorys_items_and_a_second_run_keeps_one_copy(self):
        """Github writes only this repository's usage items and a rerun keeps one copy of each"""
        self.remote()
        self.routes()
        for _ in range(2):
            code, out = self.gate("--year", "2026", "--month", "11")
            self.assertEqual(code, 0, out)
        lines = self.lines()
        self.assertEqual([l["quantity"] for l in lines], [12.0, 5.0])
        self.assertEqual(set(lines[0]), {"date", "product", "sku", "quantity", "unitType", "netAmount", "repositoryName"})
        from gate.records import unclassified, well_typed
        self.assertTrue(all(unclassified("github", l) == [] and well_typed("github", l) for l in lines))
        self.assertEqual({l["repositoryName"] for l in lines}, {"kit"})
        with open(os.path.join(self.local, "github-storage.json")) as handle:
            storage = json.load(handle)
        self.assertEqual((storage["artifacts_bytes"], storage["caches_bytes"]), (150, 4096))
        self.assertTrue(storage["fetched"])
        billing = [c for c in self.calls() if "billing" in " ".join(c)]
        self.assertTrue(any("year=2026" in " ".join(c) and "month=11" in " ".join(c) for c in billing), billing)
        self.assertTrue(any("2026-03-10" in " ".join(c) for c in billing), billing)

    def test_github_follows_every_page_of_artifacts(self):
        """Github sums unexpired artifacts across every page"""
        self.remote()
        self.routes()
        with open(self.stub) as handle:
            cfg = json.load(handle)
        full = [{"size_in_bytes": 1, "expired": False}] * 100
        cfg["routes"]["/repos/zak/kit/actions/artifacts?per_page=100&page=1"] = {"artifacts": full}
        cfg["routes"]["/repos/zak/kit/actions/artifacts?per_page=100&page=2"] = {"artifacts": [{"size_in_bytes": 7, "expired": False}]}
        with open(self.stub, "w") as handle:
            json.dump(cfg, handle)
        self.gate("--year", "2026", "--month", "11")
        with open(os.path.join(self.local, "github-storage.json")) as handle:
            self.assertEqual(json.load(handle)["artifacts_bytes"], 107)

    def test_github_for_another_month_adds_its_lines_and_keeps_the_first_months(self):
        """Github for another month adds that month's lines and keeps the first month's"""
        self.remote()
        self.routes()
        self.gate("--year", "2026", "--month", "11")
        self.routes(billing={"usageItems": OCT})
        code, out = self.gate("--year", "2026", "--month", "10")
        self.assertEqual(code, 0, out)
        self.assertEqual([l["quantity"] for l in self.lines()], [12.0, 5.0, 7.0])

    def test_github_defaults_to_the_current_month(self):
        """Github without arguments asks for the current month"""
        import datetime
        self.remote()
        self.routes()
        shutil.rmtree(self.local)  # the records folder is made when it is missing
        self.gate()
        self.assertTrue(os.path.isfile(os.path.join(self.local, "github-storage.json")))
        now = datetime.date.today()
        self.assertTrue(any("year=%d" % now.year in " ".join(c) and "month=%d" % now.month in " ".join(c) for c in self.calls()))

    def test_github_calls_an_organisation_through_the_organisation_form(self):
        """Github calls an organisation owner through the organisation form"""
        self.remote()
        self.routes(owner_type="Organization")
        code, out = self.gate("--year", "2026", "--month", "11")
        self.assertEqual(code, 0, out)
        urls = [a for c in self.calls() for a in c if a.startswith("/")]
        self.assertTrue(any(u.startswith("/organizations/zak/settings/billing/usage") for u in urls), urls)
        self.assertFalse(any(u.startswith("/users/zak/settings") for u in urls), urls)
        self.assertEqual(len(self.lines()), 2)

    def test_github_with_billing_refused_403_names_a_classic_token_and_the_role(self):
        """Github with billing refused 403 names a classic token and the role, not a Plan permission"""
        self.remote()
        self.routes(billing={"error": "gh: Resource not accessible by personal access token (HTTP 403)"})
        code, out = self.gate("--year", "2026", "--month", "11")
        self.assertEqual(code, 0, out)
        self.assertIn("personal access token (classic)", out)
        self.assertIn("billing manager", out)
        self.assertNotIn("Plan read permission", out)
        self.assertTrue(os.path.isfile(os.path.join(self.local, "github-storage.json")))
        self.assertFalse(os.path.exists(os.path.join(self.local, "github.jsonl")))

    def test_github_with_billing_404_says_the_report_is_not_available_for_the_owner(self):
        """Github with billing 404 says the billing report is not available for the owner"""
        self.remote()
        self.routes(billing={"error": "gh: Not Found (HTTP 404)"})
        code, out = self.gate("--year", "2026", "--month", "11")
        self.assertEqual(code, 0, out)
        self.assertIn("the billing report is not available for zak", out)
        self.assertNotIn("classic", out)
        self.assertTrue(os.path.isfile(os.path.join(self.local, "github-storage.json")))

    def test_github_with_the_owner_lookup_failing_skips_billing_and_says_so(self):
        """Github with the owner lookup failing says the type could not be read and skips billing"""
        self.remote()
        self.routes(owner=False)
        code, out = self.gate("--year", "2026", "--month", "11")
        self.assertEqual(code, 0, out)
        self.assertIn("owner's type could not be read", out)
        self.assertFalse(any("billing" in " ".join(c) for c in self.calls()))
        self.assertTrue(os.path.isfile(os.path.join(self.local, "github-storage.json")))

    def test_github_keeps_items_whose_repository_name_is_owner_slash_repo(self):
        """Github keeps items named owner/repo, in any case"""
        self.remote()
        items = [dict(i, repositoryName="Zak/Kit" if i["repositoryName"] == "kit" else i["repositoryName"]) for i in ITEMS]
        self.routes(billing={"usageItems": items})
        code, out = self.gate("--year", "2026", "--month", "11")
        self.assertEqual(code, 0, out)
        self.assertEqual([l["quantity"] for l in self.lines()], [12.0, 5.0])

    def test_github_with_no_item_matching_keeps_the_months_lines_and_says_so(self):
        """Github with no item matching keeps the month's existing lines and says no item matched"""
        self.remote()
        self.routes()
        self.gate("--year", "2026", "--month", "11")
        self.routes(billing={"usageItems": [ITEMS[1]]})
        code, out = self.gate("--year", "2026", "--month", "11")
        self.assertEqual(code, 0, out)
        self.assertIn("no usage item matched", out)
        self.assertEqual([l["quantity"] for l in self.lines()], [12.0, 5.0])

    def test_github_records_why_usage_is_missing_in_the_storage_file(self):
        """Github writes the usage line it printed into github-storage.json when usage is missing"""
        self.remote()
        self.routes(billing={"error": "gh: Not Found (HTTP 404)"})
        code, out = self.gate("--year", "2026", "--month", "11")
        with open(os.path.join(self.local, "github-storage.json")) as handle:
            storage = json.load(handle)
        self.assertEqual(storage["usage"], out.strip().splitlines()[0])
        self.routes()
        self.gate("--year", "2026", "--month", "11")
        with open(os.path.join(self.local, "github-storage.json")) as handle:
            self.assertNotIn("usage", json.load(handle))

    def test_github_with_gh_not_answering_exits_0_within_the_deadline_and_says_it_did_not_answer(self):
        """Github with gh auth status not answering exits 0 and says gh did not answer"""
        import time
        self.remote()
        self.routes(auth_sleep=5)
        start = time.monotonic()
        code, out = self.gate(extra={"GATE_GH_AUTH_TIMEOUT": "1"})
        self.assertEqual(code, 0, out)
        self.assertIn("gh did not answer", out)
        self.assertNotIn("signed out", out)
        self.assertLess(time.monotonic() - start, 4)

    def test_github_drops_an_unreadable_line_it_would_have_kept(self):
        """Github reads github.jsonl through the page's reader and drops an unreadable line"""
        self.remote()
        self.routes(billing={"usageItems": OCT})
        os.makedirs(self.local, exist_ok=True)
        with open(os.path.join(self.local, "github.jsonl"), "w") as handle:
            handle.write("not json\n")
        code, out = self.gate("--year", "2026", "--month", "10")
        self.assertEqual(code, 0, out)
        self.assertIn("1 unreadable", out)
        self.assertEqual([l["quantity"] for l in self.lines()], [7.0])

    def test_github_with_billing_refused_401_names_a_classic_token(self):
        """Github with billing refused 401 names a classic token too"""
        self.remote()
        self.routes(billing={"error": "gh: Bad credentials (HTTP 401)"})
        code, out = self.gate("--year", "2026", "--month", "11")
        self.assertIn("personal access token (classic)", out)

    def test_github_with_an_empty_report_replaces_the_months_lines_without_saying_no_item_matched(self):
        """Github with a report of no items replaces the month's lines and does not say no item matched"""
        self.remote()
        self.routes()
        self.gate("--year", "2026", "--month", "11")
        self.routes(billing={"usageItems": []})
        code, out = self.gate("--year", "2026", "--month", "11")
        self.assertNotIn("no usage item matched", out)
        self.assertEqual(self.lines(), [])

    def test_github_calls_never_wait_longer_than_the_deadline_has_left(self):
        """Github call timeouts are the limit or what is left of the deadline"""
        import time
        from gate import github
        github._started[0] = time.monotonic()
        self.assertLess(github._timeout(github.CALL_TIMEOUT), github.CALL_TIMEOUT + 1)
        github._started[0] = time.monotonic() - github.DEADLINE + 5
        self.assertLessEqual(github._timeout(github.CALL_TIMEOUT), 5)
        github._started[0] = time.monotonic() - github.DEADLINE - 50
        self.assertEqual(github._timeout(github.CALL_TIMEOUT), 1.0)

    def test_github_with_no_remote_says_so_in_one_line_and_writes_nothing(self):
        """Github with no GitHub remote prints one line, writes nothing and exits 0"""
        self.routes()
        code, out = self.gate()
        self.assertEqual(code, 0, out)
        self.assertEqual(len(out.strip().splitlines()), 1, out)
        self.assertIn("no GitHub remote", out)
        self.assertFalse(os.path.exists(os.path.join(self.local, "github-storage.json")))
        self.remote("https://example.com/zak/kit.git")
        code, out = self.gate()
        self.assertEqual((code, len(out.strip().splitlines())), (0, 1), out)
        self.assertIn("no GitHub remote", out)

    def test_github_with_no_gh_on_path_says_so_in_one_line_and_writes_nothing(self):
        """Github with no gh on PATH prints one line, writes nothing and exits 0"""
        self.remote()
        self.routes()
        empty = tempfile.mkdtemp(prefix="no-gh-")
        self.addCleanup(shutil.rmtree, empty, True)
        os.symlink(shutil.which("git"), os.path.join(empty, "git"))
        code, out = self.gate(path=empty)
        self.assertEqual(code, 0, out)
        self.assertEqual(len(out.strip().splitlines()), 1, out)
        self.assertIn("gh is not on PATH", out)
        self.assertFalse(os.path.exists(os.path.join(self.local, "github-storage.json")))

    def test_github_with_gh_signed_out_says_so_in_one_line_and_writes_nothing(self):
        """Github with gh signed out prints one line, writes nothing and exits 0"""
        self.remote()
        self.routes(signed_in=False)
        code, out = self.gate()
        self.assertEqual(code, 0, out)
        self.assertEqual(len(out.strip().splitlines()), 1, out)
        self.assertIn("gh is signed out", out)
        self.assertFalse(os.path.exists(os.path.join(self.local, "github-storage.json")))

    def test_github_with_storage_unreadable_still_exits_0_with_one_line(self):
        """Github with an endpoint failing says so and exits 0"""
        self.remote()
        self.routes(storage=False)
        code, out = self.gate("--year", "2026", "--month", "11")
        self.assertEqual(code, 0, out)
        self.assertIn("storage", out)
        self.assertEqual(len(self.lines()), 2)

    def test_github_with_the_recorded_bad_network_text_quotes_the_x_line_and_asks_for_the_host(self):
        """Github with gh auth status exiting 1 with the recorded text quotes the X line's cause, not the host name, and passes --hostname github.com"""
        self.remote()
        self.routes(signed_in=False, auth_text=BAD_NETWORK)
        code, out = self.gate()
        self.assertEqual(code, 0, out)
        self.assertIn("Failed to log in to github.com using token", out)
        self.assertNotIn("(github.com)", out)
        self.assertNotIn("gh auth login", out)
        self.assertIn(["auth", "status", "--hostname", "github.com"], self.calls()[:1])

    def test_github_with_billing_and_storage_both_failing_on_a_first_run_leaves_the_reason(self):
        """Github with billing and storage both failing and no storage file yet writes the usage reason to github-storage.json"""
        self.remote()
        self.routes(billing={"error": "gh: Bad credentials (HTTP 401)"}, storage=False)
        self.gate("--year", "2026", "--month", "11")
        with open(os.path.join(self.local, "github-storage.json")) as handle:
            kept = json.load(handle)
        self.assertIn("(401)", kept["usage"])
        self.assertNotIn("artifacts_bytes", kept)

    def test_github_with_auth_status_failing_for_another_reason_quotes_it_and_does_not_send_to_login(self):
        """Github with gh auth status failing on a network error quotes its first line, not gh auth login"""
        self.remote()
        self.routes(signed_in=False, auth_text="error connecting to api.github.com\ncheck your internet")
        code, out = self.gate()
        self.assertEqual(code, 0, out)
        self.assertIn("error connecting to api.github.com", out)
        self.assertNotIn("gh auth login", out)
        self.assertNotIn("check your internet", out)

    def test_github_with_auth_status_failing_silently_says_signed_out(self):
        """Github with gh auth status exiting 1 with no text says signed out"""
        self.remote()
        self.routes(signed_in=False, auth_text="")
        code, out = self.gate()
        self.assertIn("gh is signed out", out)

    def test_github_with_billing_refused_401_names_401_and_not_403(self):
        """Github with billing refused 401 names the status it received"""
        self.remote()
        self.routes(billing={"error": "gh: Bad credentials (HTTP 401)"})
        code, out = self.gate("--year", "2026", "--month", "11")
        self.assertIn("(401)", out)
        self.assertNotIn("(403)", out)

    def test_github_with_billing_and_storage_both_failing_replaces_a_stale_usage_reason(self):
        """Github with billing and storage both failing writes today's usage reason over an older one"""
        self.remote()
        self.routes(billing={"error": "gh: Not Found (HTTP 404)"})
        self.gate("--year", "2026", "--month", "11")
        self.routes(billing={"error": "gh: Bad credentials (HTTP 401)"}, storage=False)
        code, out = self.gate("--year", "2026", "--month", "11")
        with open(os.path.join(self.local, "github-storage.json")) as handle:
            self.assertIn("(401)", json.load(handle)["usage"])
        self.routes(storage=False)
        self.gate("--year", "2026", "--month", "11")
        with open(os.path.join(self.local, "github-storage.json")) as handle:
            self.assertNotIn("usage", json.load(handle))

    def test_github_with_wrong_arguments_prints_the_usage_line_and_exits_2(self):
        """Github with wrong arguments prints the usage line and exits 2"""
        repo = Repo()
        for args in (("github", "--year", "2026"), ("github", "--year", "x", "--month", "11"),
                     ("github", "--year", "2026", "--month", "13"), ("github", "--year", "2026", "--month", "0"), ("github", "extra")):
            with self.subTest(args=args):
                code, out = repo.gate(*args)
                self.assertEqual(code, 2, out)
                self.assertIn("usage: github [--year YYYY --month MM]", out)


if __name__ == "__main__":
    unittest.main()
