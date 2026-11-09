"""The dashboard page: figures from the records, every empty section naming its command, no scores, no fixed roles.

Lacks: records from a real build (the fixtures hold two small builds, one model pair, one month of usage); a page opened in a browser; a build whose names are long or numerous.

Run: python3 -B -m unittest discover -s kit/_claude/factory/tests
"""
import json
import os
import re
import subprocess
import unittest

from fixtures import CLEAN_ENV, Repo

from gate import cli

GB = 1024 ** 3
PRICES = {"claude-sonnet-5-5": {"input": 3, "output": 15}, "claude-opus-5-5": {"input": 15, "output": 75}}


def jsonl(*records):
    return "".join(json.dumps(r) + "\n" for r in records)


def build(feature, date, tickets, tried, survived, **more):
    return {"date": date, "feature": feature, "tip": "abc1234", "tickets": tickets, "reviews": tickets, "blocking": 2,
            "mutants_tried": tried, "mutants_survived": survived, "boxes_proved": 8, "boxes_human": 1,
            "subagents": {"implementer": tickets}, "guard_refusals": 0, "hours": 2.5, **more}


def escape(feature, found_by, should, n):
    return {"date": "2026-11-05", "feature": feature, "id": "E-%03d" % n, "class": "blocking", "found_by": found_by,
            "should_have_been": should, "fixed_in": "01", "rule_id": "", "flake": ""}


def token(feature, role, model, ticket="01", **kinds):
    return {"date": "2026-11-05", "feature": feature, "ticket": ticket, "role": role, "agent": "a1", "model": model,
            "input": kinds.get("input", 0), "output": kinds.get("output", 0), "cache_read": kinds.get("cache_read", 0), "cache_write": kinds.get("cache_write", 0)}


def usage(day, product, quantity, unit, net):
    return {"date": day, "product": product, "sku": product, "quantity": quantity, "unitType": unit, "netAmount": net, "repositoryName": "o/r"}


def kpi(page, label):
    found = re.search(r'<div class="kpi-label">%s</div><div class="kpi-value">([^<]*)</div>' % re.escape(label), page)
    assert found, "no KPI %r on the page" % label
    return found.group(1)


def full_repo(prices=PRICES):
    repo = Repo(extra={"prices": prices} if prices else None)
    local = "docs/agents/local/"
    repo.write(local + "builds.jsonl", jsonl(build("alpha", "2026-11-01", 4, 10, 2), build("beta", "2026-11-05", 4, 20, 3)))
    repo.write(local + "escapes.jsonl", jsonl(escape("alpha", "branch-review", "unit", 1), escape("beta", "user", "walk", 2), escape("beta", "branch-review", "unit", 3), escape("beta", "branch-review", "unit", 4)))
    repo.write(local + "tokens.jsonl", jsonl(
        token("alpha", "implementer", "claude-sonnet-5-5", input=10000),
        token("beta", "implementer", "claude-sonnet-5-5", input=100000, output=20000),
        token("beta", "orchestrator", "claude-opus-5-5", ticket="-", input=30000, output=10000)))
    repo.write(local + "flakes.jsonl", jsonl(
        {"date": "2026-11-05", "feature": "beta", "file": "w/a", "title": "the form opens", "tip": "abc1234"},
        {"date": "2026-11-05", "feature": "alpha, beta", "file": "w/a", "title": "the form opens", "tip": "def5678"}))
    repo.write(local + "github.jsonl", jsonl(usage("2026-11-02", "actions", 30, "Minutes", 0.24), usage("2026-11-03", "actions", 45, "Minutes", 0.36),
                                             usage("2026-11-03", "shared storage", 1.5, "gb-hours", 0.01)))
    repo.write(local + "github-storage.json", json.dumps({"artifacts_bytes": GB, "caches_bytes": GB, "fetched": "2026-11-05T08:00:00Z"}))
    return repo


def page_of(repo, *args):
    code, out = repo.gate("dashboard", *args)
    assert code == 0, out
    path = out.split("dashboard: ", 1)[1].split("\n")[0].strip()
    with open(path, encoding="utf-8") as handle:
        return handle.read(), path, out


class Figures(unittest.TestCase):
    def test_kpis_equal_the_fixture_arithmetic(self):
        """Dashboard KPIs equal the fixture's arithmetic"""
        page, _, _ = page_of(full_repo())
        self.assertEqual(kpi(page, "Escapes per ticket"), "0.75")
        self.assertEqual(kpi(page, "Found by you"), "1")
        self.assertEqual(kpi(page, "Tokens per ticket"), "40k")
        self.assertEqual(kpi(page, "Build cost"), "$1.80")
        self.assertEqual(kpi(page, "Surviving mutants"), "3/20")
        self.assertEqual(kpi(page, "Flakes"), "2")
        self.assertEqual(kpi(page, "GitHub Actions"), "75 min")
        self.assertEqual(kpi(page, "GitHub storage"), "2.0 GB")

    def test_found_by_you_is_second_on_the_kpi_row(self):
        """Found by you is second on the KPI row"""
        page, _, _ = page_of(full_repo())
        labels = re.findall(r'<div class="kpi-label">([^<]*)</div>', page)
        self.assertEqual(labels[:2], ["Escapes per ticket", "Found by you"])

    def test_deltas_compare_with_the_previous_build(self):
        """Dashboard KPIs show their change against the previous build"""
        page, _, _ = page_of(full_repo())
        self.assertIn('<span class="delta bad">+0.50 vs last</span>', page)  # escapes per ticket: 0.25 then 0.75, worse
        self.assertIn('<span class="delta bad">+38k vs last</span>', page)  # tokens per ticket: 2.5k then 40k, worse

    def test_a_build_of_no_tickets_has_no_escapes_per_ticket(self):
        """A build with no tickets shows 0.00 escapes per ticket, not a division"""
        repo = full_repo()
        repo.write("docs/agents/local/builds.jsonl", jsonl(build("beta", "2026-11-05", 0, 0, 0)))
        page, _, _ = page_of(repo)
        self.assertEqual(kpi(page, "Escapes per ticket"), "0.00")
        self.assertEqual(kpi(page, "Tokens per ticket"), "0")

    def test_storage_under_a_kilobyte_is_shown_in_bytes(self):
        """GitHub storage below 1024 bytes is shown in bytes, not rounded up"""
        repo = full_repo()
        repo.write("docs/agents/local/github-storage.json", json.dumps({"artifacts_bytes": 1000, "caches_bytes": 0, "fetched": "x"}))
        page, _, _ = page_of(repo)
        self.assertEqual(kpi(page, "GitHub storage"), "1000.0 B")

    def test_the_github_figures_are_the_latest_month_and_name_it(self):
        """The GitHub Actions tile and card show the later month only, and name it"""
        repo = full_repo()
        local = "docs/agents/local/"
        with open(os.path.join(repo.root, local + "github.jsonl"), "a", encoding="utf-8") as handle:
            handle.write(jsonl(usage("2026-10-02", "actions", 1000, "Minutes", 8.0)))
        page, _, _ = page_of(repo)
        self.assertEqual(kpi(page, "GitHub Actions"), "75 min")
        card = page.split("GitHub Actions minutes", 1)[1].split("</section>", 1)[0]
        self.assertIn("2026-11", card)
        self.assertNotIn("1075", page)
        self.assertIn("$0.60 in 2026-11", page)

    def test_two_storage_items_on_one_day_are_summed_in_gb_hours(self):
        """Two storage items on one day are summed in GB-hours and the tile says current storage"""
        repo = full_repo()
        with open(os.path.join(repo.root, "docs/agents/local/github.jsonl"), "a", encoding="utf-8") as handle:
            handle.write(jsonl(usage("2026-11-03", "shared storage", 0.5, "gb-hours", 0.01)))
        page, _, _ = page_of(repo)
        card = page.split("GitHub shared storage", 1)[1].split("</section>", 1)[0]
        self.assertIn("GB-hours", page.split("<h2>GitHub shared storage", 1)[1].split("</h2>", 1)[0])
        self.assertIn(">2 GB-hours<", card)
        self.assertIn("current storage", page.split('kpi-label">GitHub storage', 1)[1][:500])

    def test_items_are_classed_by_unit_type_not_product(self):
        """An item in minutes counts as Actions minutes and one in GB-hours as storage, whatever its product"""
        repo = full_repo()
        repo.write("docs/agents/local/github.jsonl", jsonl(usage("2026-11-02", "copilot", 12, "Minutes", 0.1), usage("2026-11-02", "copilot", 3, "GB-hours", 0.02)))
        page, _, _ = page_of(repo)
        self.assertEqual(kpi(page, "GitHub Actions"), "12 min")
        card = page.split("GitHub shared storage", 1)[1].split("</section>", 1)[0]
        self.assertIn(">3 GB-hours<", card)

    def test_storage_in_gb_hours_spellings_is_summed_and_gigabytes_is_named_among_other_units(self):
        """Items in GigabyteHours and gb-hours sum on the storage card; an item in gigabytes is not storage and is named among the other units"""
        repo = full_repo()
        repo.write("docs/agents/local/github.jsonl", jsonl(usage("2026-11-02", "s", 1, "GigabyteHours", 0.01), usage("2026-11-02", "s", 2, "gigabytes", 0.01), usage("2026-11-02", "s", 4, "gb-hours", 0.01)))
        page, _, _ = page_of(repo)
        card = page.split("GitHub shared storage", 1)[1].split("</section>", 1)[0]
        self.assertIn(">5 GB-hours<", card)
        self.assertIn("2 gigabytes", card)
        self.assertNotIn("No usage recorded", card)

    def test_a_large_other_unit_quantity_prints_without_exponent_form(self):
        """An other-unit quantity of 1234567 prints in full, not as 1.23457e+06"""
        repo = full_repo()
        repo.write("docs/agents/local/github.jsonl", jsonl(usage("2026-11-02", "copilot", 1234567, "requests", 0.02)))
        page, _, _ = page_of(repo)
        self.assertIn("1234567 requests", page)
        self.assertNotIn("e+06", page)

    def test_a_month_with_no_minutes_keeps_the_actions_empty_line_and_the_other_units_note(self):
        """A month of only other-unit items keeps the Actions card's empty line with the other-units note beneath it"""
        repo = full_repo()
        repo.write("docs/agents/local/github.jsonl", jsonl(usage("2026-11-02", "copilot", 9, "requests", 0.02)))
        page, _, _ = page_of(repo)
        card = page.split("GitHub Actions minutes", 1)[1].split("</section>", 1)[0]
        self.assertIn("No usage recorded", card)
        self.assertLess(card.index("No usage recorded"), card.index("9 requests"))

    def test_a_storage_file_with_only_a_reason_reads_as_no_storage(self):
        """A github-storage.json holding only a usage reason shows no storage tile figure and repeats the reason on both cards"""
        repo = full_repo()
        os.remove(os.path.join(repo.root, "docs/agents/local/github.jsonl"))
        repo.write("docs/agents/local/github-storage.json", json.dumps({"usage": "github: billing usage was refused (403) for the token"}))
        page, _, _ = page_of(repo)
        self.assertEqual(kpi(page, "GitHub storage"), "-")
        self.assertIn("no storage yet", page.split('kpi-label">GitHub storage', 1)[1][:600])
        for heading in ("GitHub Actions minutes", "GitHub shared storage"):
            card = page.split(heading, 1)[1].split("</section>", 1)[0]
            self.assertIn("refused (403) for the token", card)

    def test_an_item_in_an_unknown_unit_is_named_not_dropped(self):
        """An item in a unit the page does not know is named with its unit and quantity, and a month of only such items is not called empty"""
        repo = full_repo()
        repo.write("docs/agents/local/github.jsonl", jsonl(usage("2026-11-02", "copilot", 9, "requests", 0.02), usage("2026-11-03", "copilot", 5, "requests", 0.02)))
        page, _, _ = page_of(repo)
        card = page.split("GitHub shared storage", 1)[1].split("</section>", 1)[0]
        self.assertIn("14 requests", card)
        self.assertNotIn("No usage recorded", card)

    def test_an_item_with_no_unit_is_named_as_such(self):
        """An item with no unitType is named '(no unit)' with its quantity"""
        repo = full_repo()
        item = usage("2026-11-02", "copilot", 3, "x", 0.02)
        del item["unitType"]
        repo.write("docs/agents/local/github.jsonl", jsonl(item))
        page, _, _ = page_of(repo)
        self.assertIn("3 (no unit)", page)

    def test_the_storage_only_path_repeats_why_usage_is_missing(self):
        """With a usage reason and no github.jsonl, both GitHub cards repeat it and do not send the user to gate.py github"""
        repo = full_repo()
        os.remove(os.path.join(repo.root, "docs/agents/local/github.jsonl"))
        repo.write("docs/agents/local/github-storage.json", json.dumps({"artifacts_bytes": GB, "caches_bytes": GB, "fetched": "x", "usage": "github: billing usage was refused (403) for the token"}))
        page, _, _ = page_of(repo)
        for heading in ("GitHub Actions minutes", "GitHub shared storage"):
            card = page.split(heading, 1)[1].split("</section>", 1)[0]
            self.assertIn("billing usage was refused (403) for the token", card)
            self.assertNotIn("gate.py github", card)

    def test_flake_where_ready_writes_it_is_in_the_flakes_section(self):
        """A flake written where ready writes it appears in the flakes section"""
        page, _, _ = page_of(full_repo())
        section = page.split("Flakes by walk", 1)[1].split("</section>", 1)[0]
        self.assertIn("the form opens", section)
        self.assertRegex(section, r"<span[^>]*>2</span>")


class OneClose(unittest.TestCase):
    """A close names a fix feature too; the page counts the two as one build."""

    def close_repo(self):
        repo = Repo(extra={"prices": {"m": {"input": 3, "output": 3, "cache_read": 3, "cache_write": 3}}})
        local = "docs/agents/local/"
        repo.write(local + "builds.jsonl", jsonl(build("w", "2026-11-01", 5, 0, 0, tip="old0001"), build("x", "2026-11-05", 10, 0, 0), build("x-review", "2026-11-05", 2, 0, 0)))
        repo.write(local + "escapes.jsonl", jsonl(escape("x", "user", "unit", 1)))
        repo.write(local + "tokens.jsonl", jsonl(token("w", "implementer", "m", input=1000000), token("x", "implementer", "m", input=9000000), token("x-review", "implementer", "m", input=1000000)))
        return repo

    def test_a_build_and_its_fix_round_are_one_close_on_the_page(self):
        """The page folds the builds of one close into one build"""
        page, _, _ = page_of(self.close_repo())
        self.assertEqual(kpi(page, "Build cost"), "$30.00")
        self.assertEqual(kpi(page, "Found by you"), "1")
        self.assertEqual(kpi(page, "Escapes per ticket"), "0.08")
        self.assertIn('<span class="delta bad">+1 vs last</span>', page)  # against the previous close, not against x
        self.assertIn("<b>x, x-review</b>", page)
        self.assertEqual(page.count("<b>x"), 1)

    def test_the_folded_build_sums_every_column_of_its_features(self):
        """The folded build's row sums tickets, blocking, boxes, subagents, hours and runs"""
        page, _, _ = page_of(self.close_repo())
        row = [r for r in re.findall(r"<tr>(.*?)</tr>", page) if "<b>x, x-review</b>" in r][0]
        cells = re.findall(r"<td>(.*?)</td>", row)
        self.assertEqual([cells[2], cells[3], cells[9], cells[10], cells[11], cells[15]], ["12", "4", "16 + 2", "12", "10.0M", "5"])
        roles = page.split("Last build by role", 1)[1].split("</table>", 1)[0]
        self.assertIn("<td>implementer</td><td>2</td><td>10.0M</td><td>5.0M</td><td>$30.00</td>", roles)

    def test_recent_escapes_list_the_last_written_of_a_day_first(self):
        """Recent escapes list the escapes written last first within a day"""
        repo = Repo()
        repo.write("docs/agents/local/escapes.jsonl", jsonl(*[escape("x", "unit", "unit", n) for n in range(1, 13)] + [escape("x", "user", "unit", 13), escape("x", "user", "unit", 14)]))
        page, _, _ = page_of(repo)
        ids = re.findall(r"<td><code>(E-\d+)</code>", page)
        self.assertEqual(ids[:3], ["E-014", "E-013", "E-012"])
        self.assertEqual(len(ids), 12)

    def test_a_feature_with_records_and_no_builds_row_shows_on_the_page(self):
        """A feature with escapes or tokens and no builds row has a row marked no builds row"""
        repo = Repo()
        local = "docs/agents/local/"
        repo.write(local + "builds.jsonl", jsonl(build("alpha", "2026-11-05", 4, 0, 0)))
        repo.write(local + "escapes.jsonl", jsonl(escape("old", "user", "walk", 1), escape("old", "user", "walk", 2)))
        repo.write(local + "tokens.jsonl", jsonl(token("older", "implementer", "m", input=5)))
        page, _, _ = page_of(repo)
        self.assertEqual(page.count("no builds row"), 2)
        self.assertEqual(kpi(page, "Found by you"), "0")  # the KPI row is still the last real build
        chart = page.split("Where failures are", 1)[1].split("</div>", 1)[0]
        self.assertIn(">old<", chart)

    def test_late_is_the_ledgers_list_and_the_footnote_names_every_gate(self):
        """The footnote under the builds table names every gate in the ledger's later gates"""
        from gate import ledger
        page, _, _ = page_of(full_repo())
        note = page.split("Late = ", 1)[1].split("</p>", 1)[0]
        for gate in ledger.LATER_GATES:
            self.assertIn(gate, note)
        self.assertFalse(hasattr(__import__("gate.dashboard", fromlist=["x"]), "LATE"))


class Columns(unittest.TestCase):
    def test_the_late_and_misclass_columns_count_late_and_misclassed_escapes(self):
        """The builds table's Late and Misclass columns count the late and the misclassed escapes of a build"""
        repo = Repo()
        local = "docs/agents/local/"
        repo.write(local + "builds.jsonl", jsonl(build("gamma", "2026-11-05", 4, 10, 2)))
        rows = [escape("gamma", "ticket-review", "unit", 1), escape("gamma", "branch-review", "unit", 2),
                dict(escape("gamma", "ready-gate", "unit", 3), **{"class": "nit"}), dict(escape("gamma", "ready-gate", "unit", 4), **{"class": "sweep"})]
        repo.write(local + "escapes.jsonl", jsonl(*rows))
        page, _, _ = page_of(repo)
        table = page.split("<thead>", 1)[1].split("</table>", 1)[0]
        heads = re.findall(r"<th>([^<]*)</th>", table)
        cells = re.findall(r"<td>(.*?)</td>", table.split("<tbody>", 1)[1], re.S)
        row = dict(zip(heads, cells))
        self.assertEqual((row["Escapes"], row["Late"], row["Misclass"]), ("4", "3", "2"))


class Absent(unittest.TestCase):
    def two_builds(self, tokens, prices=PRICES):
        repo = Repo(extra={"prices": prices} if prices else None)
        local = "docs/agents/local/"
        repo.write(local + "builds.jsonl", jsonl(build("alpha", "2026-11-01", 4, 10, 2), build("beta", "2026-11-05", 4, 20, 3)))
        repo.write(local + "tokens.jsonl", jsonl(*tokens))
        return repo

    def test_a_build_with_no_token_records_says_no_records_and_names_the_command(self):
        """A build with no token records reads no records on both tiles and in the table, never 0"""
        page, _, _ = page_of(self.two_builds([token("alpha", "implementer", "claude-sonnet-5-5", input=1000)]))
        self.assertEqual(kpi(page, "Tokens per ticket"), "no records")
        self.assertEqual(kpi(page, "Build cost"), "no records")
        self.assertIn("gate.py stats --write beta", page.split("Tokens per ticket", 1)[1].split("Surviving", 1)[0])
        row = page.split("<b>beta</b>", 1)[1].split("</tr>", 1)[0]
        self.assertIn("no records<br><code>gate.py stats --write beta</code>", row)
        self.assertNotIn("$0.00", row)
        self.assertNotIn("$0.00", page.split("Surviving", 1)[0])

    def test_no_delta_is_drawn_against_a_build_with_no_token_records(self):
        """No vs last on the token tiles when the previous build has no records"""
        page, _, _ = page_of(self.two_builds([token("beta", "implementer", "claude-sonnet-5-5", input=1000)]))
        tiles = page.split("Tokens per ticket", 1)[1].split("Surviving", 1)[0]
        self.assertNotIn("vs last", tiles)
        self.assertEqual(kpi(page, "Tokens per ticket"), "250")

    def test_a_build_with_every_model_unpriced_reads_unpriced_not_zero_dollars(self):
        """The cost tile reads unpriced, as the table does, when no record is priced"""
        page, _, _ = page_of(self.two_builds([token("alpha", "implementer", "claude-sonnet-5-5", input=1000), token("beta", "implementer", "mystery", input=1000)]))
        self.assertEqual(kpi(page, "Build cost"), "unpriced")
        self.assertNotIn("$0.00", page.split("Surviving", 1)[0])
        tiles = page.split("Build cost", 1)[1].split("Surviving", 1)[0]
        self.assertNotIn("vs last", tiles)

    def test_surviving_mutants_shows_its_change_against_the_previous_build(self):
        """The Surviving mutants tile has a vs last line (2 then 3 survivors, worse)"""
        page, _, _ = page_of(full_repo())
        self.assertIn('<span class="delta bad">+1 vs last</span>', page.split("Surviving mutants", 1)[1].split("Flakes", 1)[0])

    def test_a_build_with_no_mutants_tried_has_no_mutant_delta(self):
        """No vs last on Surviving mutants when the latest build tried none"""
        repo = full_repo()
        repo.write("docs/agents/local/builds.jsonl", jsonl(build("alpha", "2026-11-01", 4, 10, 2), build("beta", "2026-11-05", 4, 0, 0)))
        page, _, _ = page_of(repo)
        self.assertEqual(kpi(page, "Surviving mutants"), "-")
        self.assertNotIn("vs last", page.split("Surviving mutants", 1)[1].split("Flakes", 1)[0])


class Money(unittest.TestCase):
    def test_without_prices_tokens_show_and_money_does_not(self):
        """Without prices the page shows tokens and no money"""
        page, _, _ = page_of(full_repo(prices=None))
        self.assertEqual(kpi(page, "Build cost"), "160k tok")
        self.assertNotIn("$1.80", page)
        self.assertIn("prices", page.split("Build cost", 1)[1].split("</div></div>", 1)[0])

    def test_a_model_without_a_price_is_unpriced_not_zero(self):
        """With a price for one of two models the other is shown as unpriced"""
        page, _, _ = page_of(full_repo(prices={"claude-sonnet-5-5": PRICES["claude-sonnet-5-5"]}))
        value = kpi(page, "Build cost")
        self.assertIn("$0.60", value)
        self.assertIn("unpriced", value)
        self.assertIn("claude-opus-5-5", page)


class Priced(unittest.TestCase):
    ALL = {"input": 3, "output": 15, "cache_read": 0.3, "cache_write": 3.75}

    def one_build(self, prices):
        repo = Repo(extra={"prices": prices})
        local = "docs/agents/local/"
        repo.write(local + "builds.jsonl", jsonl(build("alpha", "2026-11-01", 1, 0, 0)))
        repo.write(local + "tokens.jsonl", jsonl(token("alpha", "implementer", "m", input=1000, output=1000, cache_read=10000000, cache_write=1000000)))
        return repo

    def test_a_kind_the_price_leaves_out_makes_the_record_unpriced(self):
        """A record with cache reads on a price without cache_read is unpriced on the page"""
        page, _, _ = page_of(self.one_build({"m": {"input": 3, "output": 15}}))
        self.assertIn("unpriced", kpi(page, "Build cost"))
        self.assertNotIn("$0.02", page)

    def test_every_kind_is_priced_and_dropping_any_one_changes_the_cost(self):
        """The cost counts all four kinds: dropping any kind's price changes it (to unpriced)"""
        page, _, _ = page_of(self.one_build({"m": self.ALL}))
        self.assertIn("$6.77", kpi(page, "Build cost"))
        self.assertNotIn("unpriced", kpi(page, "Build cost"))
        for kind in self.ALL:
            prices = {k: v for k, v in self.ALL.items() if k != kind}
            page, _, _ = page_of(self.one_build({"m": prices}))
            self.assertIn("unpriced", kpi(page, "Build cost"), kind)

    def test_invalid_prices_are_refused_with_config_valid_and_no_page(self):
        """dashboard refuses a factory.json config would refuse, naming the problems, and writes no page"""
        repo = self.one_build({"m": {"input": "3", "outptu": 15}})
        code, out = repo.gate("dashboard")
        self.assertEqual(code, 1, out)
        self.assertIn("refused by config-valid", out)
        self.assertGreaterEqual(out.count("factory.json: "), 2, out)
        self.assertFalse(os.path.exists(os.path.join(repo.root, ".git", "factory", "dashboard.html")))
        self.assertNotIn("dashboard: ", out)

    def test_a_list_where_a_string_belongs_is_skipped_and_counted(self):
        """A tokens line with a list role and an escapes line with a list gate are skipped, counted, and the page is written"""
        repo = full_repo()
        local = os.path.join(repo.root, "docs/agents/local/")
        with open(local + "tokens.jsonl", "a") as handle:
            handle.write(json.dumps(token("beta", ["implementer"], "claude-sonnet-5-5", input=5)) + "\n")
        with open(local + "escapes.jsonl", "a") as handle:
            handle.write(json.dumps(escape("beta", "user", ["unit"], 9)) + "\n")
        page, _, _ = page_of(repo)
        self.assertIn("2 line(s) skipped", page.split("<footer>", 1)[1])


class Typed(unittest.TestCase):
    def test_a_count_that_is_a_boolean_or_a_string_is_skipped(self):
        """A tokens line whose count is true or a string is skipped and counted"""
        from gate.records import well_typed
        self.assertTrue(well_typed("tokens", {"input": 5, "role": "implementer"}))
        self.assertFalse(well_typed("tokens", {"input": True}))
        self.assertFalse(well_typed("tokens", {"output": "5"}))

    def test_a_count_that_is_not_finite_is_skipped_and_the_page_is_written(self):
        """A builds line with NaN tickets and a tokens line with Infinity input are skipped and counted, and the page is written"""
        repo = full_repo()
        local = os.path.join(repo.root, "docs/agents/local/")
        with open(local + "builds.jsonl", "a") as handle:
            handle.write('{"date":"2026-11-01","feature":"alpha","tip":"abc","tickets":NaN}\n')
        with open(local + "tokens.jsonl", "a") as handle:
            handle.write('{"date":"2026-11-01","feature":"alpha","role":"implementer","model":"m","input":Infinity}\n')
        page, _, _ = page_of(repo)
        footer = page.split("<footer>", 1)[1]
        self.assertIn("2 line(s) skipped", footer)
        self.assertNotIn("infM", page)

    def test_the_footer_names_the_file_of_each_skipped_line(self):
        """The footer names each record file with skipped lines and how many"""
        repo = full_repo()
        local = os.path.join(repo.root, "docs/agents/local/")
        with open(local + "tokens.jsonl", "a") as handle:
            handle.write(json.dumps(token("beta", ["x"], "m", input=5)) + "\n[1]\n")
        with open(local + "escapes.jsonl", "a") as handle:
            handle.write("{broken\n")
        page, _, _ = page_of(repo)
        self.assertIn("3 line(s) skipped as unreadable or of the wrong type (escapes.jsonl 1, tokens.jsonl 2)", page.split("<footer>", 1)[1])


class Empty(unittest.TestCase):
    def test_every_input_missing_still_writes_the_page_naming_each_command(self):
        """With every input missing the page is written and each section names the command that fills it"""
        repo = Repo()
        page, _, _ = page_of(repo)
        for command in ("gate.py close", "gate.py ledger add", "gate.py stats --write", "gate.py github", "gate.py ready"):
            self.assertIn(command, page)
        for heading in ("Builds", "escapes by the gate", "by role per build", "Last build by role", "GitHub Actions minutes", "GitHub shared storage", "Flakes by walk", "Recent escapes"):
            found = re.search(r"<h2>[^<]*%s.*?(?=<h2>|<footer>)" % re.escape(heading), page, re.S)
            card = found.group(0) if found else ""
            self.assertIn("gate.py", card, heading)

    def test_unreadable_factory_json_prices_are_refused_not_a_crash(self):
        """A prices value that is not an object is refused as config refuses it, not a crash"""
        repo = full_repo(prices=None)
        with open(os.path.join(repo.root, "docs/agents/local/factory.json")) as handle:
            config = json.load(handle)
        config["prices"] = "free"
        repo.write("docs/agents/local/factory.json", json.dumps(config))
        code, out = repo.gate("dashboard")
        self.assertEqual(code, 1, out)
        self.assertIn("refused by config-valid", out)


class Shape(unittest.TestCase):
    def test_no_scores_section_and_no_column_for_a_role_in_no_record(self):
        """The page has no scores section and a role in no record has no column"""
        page, _, _ = page_of(full_repo())
        self.assertNotIn("Scorer", page)
        self.assertNotIn("scores", page.lower())
        self.assertNotIn("observer", page)
        self.assertNotIn("branch-reviewer", page)
        self.assertIn("orchestrator", page)

    def test_a_role_that_only_a_record_has_shows(self):
        """A role found in a record shows without a page change"""
        repo = full_repo()
        repo.write("docs/agents/local/tokens.jsonl", jsonl(token("beta", "novel-role", "claude-sonnet-5-5", input=5000)))
        page, _, _ = page_of(repo)
        self.assertIn("novel-role", page)

    def test_an_agent_on_two_models_is_one_run(self):
        """An agent on two models is one run in the role table"""
        repo = full_repo()
        repo.write("docs/agents/local/tokens.jsonl", jsonl(token("beta", "novel-role", "claude-sonnet-5-5", input=1000), token("beta", "novel-role", "claude-opus-5-5", input=3000)))
        page, _, _ = page_of(repo)
        self.assertRegex(page, r"novel-role</td><td>1</td><td>4k</td><td>4k</td>")

    def test_gates_are_ordered_by_the_ledgers_vocabulary(self):
        """Escape gates in the legend follow the ledger's order"""
        page, _, _ = page_of(full_repo())
        legend = page.split("escapes by the gate", 1)[1].split("</section>", 1)[0]
        self.assertLess(legend.index("walk</span>"), legend.index("unit</span>"))  # the vocabulary lists walk before unit

    def test_a_malformed_line_is_skipped_and_counted_in_the_footer(self):
        """A malformed line in any record is skipped and the footer counts the skipped lines"""
        repo = full_repo()
        for name in ("builds", "escapes", "tokens", "flakes", "github"):
            path = os.path.join(repo.root, "docs/agents/local/%s.jsonl" % name)
            with open(path, "a") as handle:
                handle.write("{not json\n[1, 2]\n")
        page, _, _ = page_of(repo)
        footer = page.split("<footer>", 1)[1]
        self.assertIn("10 line(s) skipped", footer)
        self.assertEqual(kpi(page, "Escapes per ticket"), "0.75")

    def test_a_clean_run_says_no_lines_were_skipped(self):
        """A page from clean records says 0 line(s) skipped"""
        page, _, _ = page_of(full_repo())
        self.assertIn("0 line(s) skipped", page.split("<footer>", 1)[1])

    def test_the_page_fits_a_phone_and_has_a_dark_scheme(self):
        """The page has a viewport, wraps wide tables, and a dark scheme on tokens"""
        page, _, _ = page_of(full_repo())
        self.assertIn('name="viewport"', page)
        self.assertIn("prefers-color-scheme: dark", page)
        self.assertIn("overflow-x:auto", page)
        self.assertIn("min(320px,100%)", page)
        self.assertNotIn("<script", page)
        self.assertNotRegex(page, r'(src|href)="https?:')

    def test_user_content_is_escaped(self):
        """Names from the records are escaped in the page"""
        repo = full_repo()
        repo.write("docs/agents/local/flakes.jsonl", jsonl({"date": "2026-11-05", "feature": "beta", "file": "f", "title": "<b>x</b>", "tip": "t"}))
        page, _, _ = page_of(repo)
        self.assertNotIn("<b>x</b>", page)
        self.assertIn("&lt;b&gt;x&lt;/b&gt;", page)


class Place(unittest.TestCase):
    def test_default_output_is_under_the_git_directory_and_leaves_status_clean(self):
        """The default output is under the git common directory and leaves git status clean"""
        repo = full_repo()
        repo.commit()
        _, path, out = page_of(repo)
        git_dir = subprocess.run(["git", "-C", repo.root, "rev-parse", "--absolute-git-dir"], capture_output=True, text=True, env=CLEAN_ENV).stdout.strip()
        self.assertEqual(os.path.realpath(path), os.path.realpath(os.path.join(git_dir, "factory", "dashboard.html")))
        status = subprocess.run(["git", "-C", repo.root, "status", "--porcelain"], capture_output=True, text=True, env=CLEAN_ENV).stdout
        self.assertEqual(status, "")

    def test_a_path_given_is_written_there(self):
        """Dashboard writes to the path it is given"""
        repo = full_repo()
        page, path, _ = page_of(repo, os.path.join(repo.root, "copy", "p.html"))
        self.assertTrue(path.endswith(os.path.join("copy", "p.html")))
        self.assertIn("Factory dashboard", page)

    def test_sample_is_labelled_as_invented_figures(self):
        """Dashboard --sample writes a page labelled as invented figures"""
        repo = Repo()
        page, _, _ = page_of(repo, "--sample")
        self.assertIn("invented figures", page)
        self.assertNotIn("Scorer", page)
        self.assertNotEqual(kpi(page, "Escapes per ticket"), "0.00")
        real, _, _ = page_of(repo)
        self.assertNotIn("invented figures", real)

    def test_the_module_passes_the_kits_forbid_rules(self):
        """The kit's forbid rules pass over the dashboard module"""
        here = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(os.path.dirname(here), "gate", "dashboard.py"), encoding="utf-8") as handle:
            text = handle.read()
        for pattern in (r"(?i)(?<![\w<>.-])(src|client|scripts|test|walks)/", r"\b(npm|npx|node_modules|stryker|playwright|chromium|webkit)\b", r"\.scratch/(?!<)[a-z0-9]"):
            self.assertIsNone(re.search(pattern, text), pattern)


class Routing(unittest.TestCase):
    def test_help_lists_the_three_new_commands_with_their_arguments(self):
        """Help lists dashboard, github and stats --write with their arguments"""
        doc = cli.__doc__
        self.assertIn("gate.py dashboard [<out.html>] [--sample]", doc)
        self.assertIn("gate.py github [--year YYYY --month MM]", doc)
        self.assertIn("gate.py stats --write <feature> [more]", doc)

    def test_dashboard_with_wrong_arguments_prints_the_usage_line_and_exits_2(self):
        """Dashboard with wrong arguments prints the usage line and exits 2"""
        repo = Repo()
        for args in (("dashboard", "a.html", "b.html"), ("dashboard", "--bogus")):
            with self.subTest(args=args):
                code, out = repo.gate(*args)
                self.assertEqual(code, 2, out)
                self.assertIn("usage: dashboard [<out.html>] [--sample]", out)


if __name__ == "__main__":
    unittest.main()
