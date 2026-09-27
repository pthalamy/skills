"""Regression tests for the scripts bundled with the skills.

Run with ``python3 -m unittest discover -s tests``. Standard library only.
Each test names the defect it guards against; several came from a field
test of the skills on a real family file.
"""
from __future__ import annotations

import copy
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RT = ROOT / "skills" / "record-transcriber" / "scripts"
GM = ROOT / "skills" / "gedcom-maintainer" / "scripts"
RP = ROOT / "skills" / "genealogy-research-planner" / "scripts"
GR = ROOT / "skills" / "geneanet-researcher" / "scripts"
for p in (RT, GM, RP, GR):
    sys.path.insert(0, str(p))

import gedcom_lib  # noqa: E402
import geneanet_findings as gf  # noqa: E402
import research_log  # noqa: E402
import transcription_to_gedcom as ttg  # noqa: E402
import validate_gedcom  # noqa: E402

EXAMPLE = json.loads((ROOT / "skills" / "record-transcriber" / "assets" / "example-transcription.json").read_text(encoding="utf-8"))


def gedcom_of(doc: dict, **kw) -> str:
    return ttg.to_gedcom(doc, kw.get("source_xref"), kw.get("mapping", {}), 9001, 9001, kw.get("no_text", False))


def validate_fragments(fragments: str, extra: str = "") -> tuple[dict, validate_gedcom.Findings]:
    body = "\n".join(l for l in fragments.splitlines() if not l.startswith("#"))
    text = "0 HEAD\n1 GEDC\n2 VERS 5.5.1\n1 CHAR UTF-8\n" + body + "\n" + extra + "0 TRLR\n"
    with tempfile.NamedTemporaryFile("w", suffix=".ged", delete=False, encoding="utf-8") as fh:
        fh.write(text)
    return validate_gedcom.run(fh.name)


class FrenchNumbers(unittest.TestCase):
    def test_multiplicative_forms(self):
        cases = {"vingt six": 26, "quatre vingt neuf": 89, "quatre vingts": 80, "quatre vingt dix neuf": 99,
                 "mil sept cent quatre vingt neuf": 1789, "soixante et onze": 71, "deux cents": 200,
                 "mille neuf cent trois": 1903, "cent": 100, "vingt et un": 21, "septante deux": 72, "premier": 1}
        for words, value in cases.items():
            with self.subTest(words=words):
                self.assertEqual(ttg.words_to_int(words), value)

    def test_unknown_word_is_none(self):
        self.assertIsNone(ttg.words_to_int("trente chevaux"))


class RepublicanCalendar(unittest.TestCase):
    def test_known_conversions(self):
        self.assertEqual(ttg.french_to_gregorian(4, 1, 13).isoformat(), "1795-10-05")
        self.assertEqual(ttg.french_to_gregorian(8, 2, 18).isoformat(), "1799-11-09")
        self.assertEqual(gedcom_lib.french_to_gregorian(1, 1, 1).isoformat(), "1792-09-22")

    def test_complementary_days_are_bounded(self):
        self.assertIsNone(ttg.parse_republican("30e jour complémentaire an 2"))
        self.assertEqual(ttg.parse_republican("6e jour complémentaire an 3"), (3, 13, 6))
        self.assertIsNone(ttg.parse_republican("6e jour complémentaire an 4"))
        self.assertEqual(ttg.parse_republican("5 jour complementaire an 4"), (4, 13, 5))
        self.assertTrue(gedcom_lib.parse_date("@#DFRENCH R@ 6 COMP 4").problems)
        self.assertFalse(gedcom_lib.parse_date("@#DFRENCH R@ 6 COMP 3").problems)

    def test_words_and_roman_years(self):
        self.assertEqual(ttg.parse_republican("le treize vendémiaire an quatre de la République"), (4, 1, 13))
        self.assertEqual(ttg.parse_republican("12 vendemiaire an IV"), (4, 1, 12))


class TranscriptionExport(unittest.TestCase):
    def test_example_validates_and_exports_clean_gedcom(self):
        errors, warnings = ttg.validate(EXAMPLE)
        self.assertEqual(errors, [])
        frag = gedcom_of(EXAMPLE, source_xref="@S3@", mapping={"p1": "@I12@"})
        _, f = validate_fragments(frag, "0 @S3@ SOUR\n1 TITL test\n")
        self.assertEqual(f.count("ERROR"), 0, [i["message"] for i in f.items if i["severity"] == "ERROR"])

    def test_generic_event_is_exported(self):
        doc = copy.deepcopy(EXAMPLE)
        doc["document"]["type"] = "other"
        doc["document"]["subtype"] = "arrestation"
        doc["event"] = {"type": "other", "date": {"as_written": "16 décembre 1941", "iso": "1941-12-16"},
                        "place": {"as_written": "Saint-Vallier"}, "details": "Arrêté au puits Darcy, libéré le 20 décembre 1941"}
        frag = gedcom_of(doc)
        self.assertIn("1 EVEN", frag)
        self.assertIn("2 DATE 16 DEC 1941", frag)
        self.assertIn("2 NOTE Arrêté au puits Darcy", frag)

    def test_generic_event_without_details_warns(self):
        doc = copy.deepcopy(EXAMPLE)
        doc["document"]["type"] = "other"
        doc["document"].pop("subtype", None)
        doc["event"] = {"type": "other"}
        _, warnings = ttg.validate(doc)
        self.assertTrue(any("event.type 'other'" in w for w in warnings))

    def test_derivative_source_dates_facts_by_event_not_publication(self):
        doc = copy.deepcopy(EXAMPLE)
        doc["document"]["source_type"] = "authored"
        doc["document"]["act_date"] = {"as_written": "2016", "iso": "2016"}
        doc["event"] = {"type": "other", "date": {"as_written": "décembre 1941", "iso": "1941-12"}, "details": "arrestation"}
        for p in doc["persons"]:
            p.pop("age", None)
        doc["persons"][1]["age"] = {"as_written": "38 ans", "years": 38, "qualifier": "exact"}
        frag = gedcom_of(doc)
        self.assertNotIn("2 DATE 2016", frag.split("0 @S9001@ SOUR")[0] if "0 @S9001@ SOUR" in frag else frag)
        self.assertIn("1 OCCU tisseur\n2 DATE DEC 1941", frag)
        self.assertIn("2 DATE CAL 1903", frag)  # 1941 - 38, not 2016 - 38
        # a derivative record is never QUAY 3
        self.assertNotIn("3 QUAY 3", frag)

    def test_derivative_without_event_date_carries_no_fact_dates(self):
        doc = copy.deepcopy(EXAMPLE)
        doc["document"]["source_type"] = "derivative"
        doc["document"]["act_date"] = {"as_written": "2016", "iso": "2016"}
        doc["event"] = {"type": "other", "details": "index entry"}
        _, warnings = ttg.validate(doc)
        self.assertTrue(any("derivative/authored source without event.date" in w for w in warnings))
        frag = gedcom_of(doc)
        self.assertNotIn("1 OCCU tisseur\n2 DATE", frag)

    def test_officiant_never_produces_dangling_asso(self):
        doc = copy.deepcopy(EXAMPLE)
        doc["persons"].append({"id": "p9", "role": "officiant", "related_to": "p1",
                               "names": {"given_as_written": "Claude", "surname_as_written": "Rey"}})
        frag = gedcom_of(doc)
        self.assertIn("Officiant: Claude Rey", frag)
        _, f = validate_fragments(frag)
        self.assertEqual([i["message"] for i in f.items if i["code"].startswith("pointer")], [])

    def test_marriage_with_divorce_mention(self):
        doc = copy.deepcopy(EXAMPLE)
        doc["document"]["type"] = "marriage"
        doc["document"]["act_date"] = {"as_written": "15 juin 1842", "iso": "1842-06-15"}
        doc["event"] = {"type": "marriage", "date": {"as_written": "15 juin 1842", "iso": "1842-06-15"}}
        doc["persons"] = [
            {"id": "p1", "role": "subject", "party": 1, "names": {"given_as_written": "Louis", "surname_as_written": "Bernard"}, "sex": "M"},
            {"id": "p2", "role": "subject", "party": 2, "names": {"given_as_written": "Louise", "surname_as_written": "Dupont"}, "sex": "F"},
        ]
        doc["marginal_mentions"] = [{"type": "divorce", "date": {"as_written": "3 mars 1860", "iso": "1860-03-03"}, "text": "Divorcé", "persons": ["p1", "p2"]}]
        errors, _ = ttg.validate(doc)
        self.assertEqual(errors, [])
        frag = gedcom_of(doc)
        self.assertIn("1 MARR\n2 DATE 15 JUN 1842", frag)
        self.assertIn("1 DIV\n2 DATE 3 MAR 1860", frag)
        _, f = validate_fragments(frag)
        self.assertEqual(f.count("ERROR"), 0)

    def test_long_text_is_wrapped_under_255(self):
        doc = copy.deepcopy(EXAMPLE)
        doc["transcription"]["literal"] = "mot " * 400
        frag = gedcom_of(doc)
        self.assertTrue(all(len(l) <= 255 for l in frag.splitlines()))


class GedcomValidator(unittest.TestCase):
    def _run(self, body: str):
        text = "0 HEAD\n1 GEDC\n2 VERS 5.5.1\n1 CHAR UTF-8\n" + body + "0 TRLR\n"
        with tempfile.NamedTemporaryFile("w", suffix=".ged", delete=False, encoding="utf-8") as fh:
            fh.write(text)
        return validate_gedcom.run(fh.name)[1]

    def test_reciprocal_links_and_chronology(self):
        f = self._run("0 @I1@ INDI\n1 NAME Jean /Dupont/\n1 SEX M\n1 BIRT\n2 DATE 31 FEB 1850\n1 DEAT\n2 DATE 1840\n1 FAMS @F1@\n"
                      "0 @I2@ INDI\n1 NAME Marie /Martin/\n1 SEX F\n0 @F1@ FAM\n1 HUSB @I1@\n1 WIFE @I2@\n1 CHIL @I1@\n")
        codes = {i["code"] for i in f.items}
        for expected in ("chrono.deathbeforebirth", "link.fams", "link.famc", "role.selfparent", "date.syntax"):
            self.assertIn(expected, codes)

    def test_clean_file_has_no_errors(self):
        f = self._run("0 @I1@ INDI\n1 NAME Jean /Dupont/\n1 SEX M\n1 BIRT\n2 DATE @#DFRENCH R@ 12 VEND 4\n1 FAMS @F1@\n"
                      "0 @I2@ INDI\n1 NAME Marie /Martin/\n1 SEX F\n1 BIRT\n2 DATE ABT 1797\n1 FAMS @F1@\n"
                      "0 @F1@ FAM\n1 HUSB @I1@\n1 WIFE @I2@\n1 MARR\n2 DATE 15 JUN 1818\n")
        self.assertEqual(f.count("ERROR"), 0)
        self.assertEqual(f.count("WARNING"), 0)


class ResearchLog(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.log = str(Path(self.dir) / "log.json")
        self._call(["init", self.log])
        self._call(["question", self.log, "add", "Find X"])

    def _call(self, argv, expect_exit=None):
        out = io.StringIO()
        try:
            with redirect_stdout(out):
                code = research_log.main(argv)
        except SystemExit as exc:
            code = exc.code
        if expect_exit is not None:
            self.assertEqual(code if isinstance(code, int) else 1, expect_exit, out.getvalue())
        return out.getvalue()

    def test_negative_requires_scope_on_add(self):
        self._call(["add", self.log, "--question", "Q1", "--record", "r", "--repository", "AD", "--result", "negative"], expect_exit=1)

    def test_done_cannot_bypass_scope_rule(self):
        self._call(["add", self.log, "--question", "Q1", "--record", "r", "--repository", "AD", "--result", "pending"])
        self._call(["done", self.log, "S1", "negative"], expect_exit=1)
        self._call(["done", self.log, "S1", "negative", "--scope", "Lyon 1815-1820"], expect_exit=0)
        data = json.loads(Path(self.log).read_text())
        self.assertEqual(data["searches"][0]["result"], "negative")
        self.assertEqual(data["searches"][0]["scope"], "Lyon 1815-1820")

    def test_report_lists_pending(self):
        self._call(["add", self.log, "--question", "Q1", "--record", "r", "--repository", "AD", "--result", "pending", "--scope", "x"])
        report = self._call(["report", self.log])
        self.assertIn("## Next actions", report)
        self.assertIn("S1 (pending)", report)


class GeneanetFindings(unittest.TestCase):
    EXAMPLE = json.loads((ROOT / "skills" / "geneanet-researcher" / "assets" / "findings-example.json").read_text(encoding="utf-8"))

    def test_search_url_always_has_go(self):
        url = gf.search_url("DUBOIS", "Jeanne Rosalie", "Bresles", 1850, 1890)
        self.assertIn("go=1", url)
        self.assertIn("prenom=Jeanne+Rosalie", url)
        self.assertIn("place__0__=Bresles", url)
        self.assertIn("type_periode=between&from=1850&to=1890", url)
        with self.assertRaises(ValueError):
            gf.search_url("DUBOIS", size=25)

    def test_person_url_key(self):
        self.assertEqual(gf.person_url("Abc", "Dubois", "Marie-Thérèse Joseph", 2),
                         "https://gw.geneanet.org/abc?lang=fr&n=dubois&oc=2&p=marie+therese+joseph")

    def test_robots_snapshot(self):
        self.assertEqual(gf.robots_verdict("https://gw.geneanet.org/abc?lang=fr&m=A&n=x&p=y")[0], "disallowed")
        self.assertEqual(gf.robots_verdict("https://gw.geneanet.org/abc?lang=fr&m=N&v=x")[0], "allowed")
        self.assertEqual(gf.robots_verdict("https://gw.geneanet.org/abc?lang=fr&n=x&p=y")[0], "allowed")
        self.assertEqual(gf.robots_verdict("https://www.geneanet.org/cercles/view/x/1")[0], "disallowed")
        self.assertEqual(gf.robots_verdict("https://www.geneanet.org/releves-collaboratifs/view/1/2")[0], "allowed")

    def test_refs_extracts_cote_view_and_labelled_segment(self):
        ref = gf.extract_refs("Registre Bresles NMD années 1860-1870 côte archives 3E999/4 vue 52/300 - Original", "birth")
        self.assertEqual(ref["cote"], "3E999/4")
        self.assertEqual(ref["view"], "52/300")
        block = "Naissance: Archives Oise, image 52\nUnion: Archives Oise, images 210, 211 et 212"
        self.assertEqual(gf.extract_refs(block, "birth")["view"], "52")
        tree = gf.extract_refs("arbre https://gw.geneanet.org/other?lang=fr&n=x&p=y", "birth")
        self.assertIn("cites", tree)
        self.assertNotIn("url", tree)

    def test_example_validates_and_reports(self):
        errors, warnings = gf.check(self.EXAMPLE)
        self.assertEqual(errors, [])
        self.assertTrue(any("F6" in w and "names only" in w for w in warnings))
        report = gf.build_report(self.EXAMPLE)
        self.assertIn("## Records to open", report)
        self.assertIn("cote 3E999/4", report)
        self.assertIn("**Conflict on death:**", report)

    def test_unsourced_with_source_text_is_an_error(self):
        doc = copy.deepcopy(self.EXAMPLE)
        doc["findings"][2]["source_verbatim"] = "something"
        errors, _ = gf.check(doc)
        self.assertTrue(any("status unsourced" in e for e in errors))

    def test_log_export_is_idempotent(self):
        d = Path(tempfile.mkdtemp())
        findings, log = d / "f.json", d / "log.json"
        findings.write_text(json.dumps(self.EXAMPLE), encoding="utf-8")
        with redirect_stdout(io.StringIO()):
            research_log.main(["init", str(log)])
            research_log.main(["question", str(log), "add", "Find X"])
            gf.main(["log", str(findings), str(log), "--question", "Q1"])
            first = len(json.loads(log.read_text())["searches"])
            gf.main(["log", str(findings), str(log), "--question", "Q1"])
        data = json.loads(log.read_text())
        self.assertEqual(len(data["searches"]), first)
        self.assertTrue(any(s["result"] == "pending" for s in data["searches"]))
        negatives = [s for s in data["searches"] if s["result"] == "negative"]
        self.assertTrue(negatives and all(s["scope"] for s in negatives))


class CommandLine(unittest.TestCase):
    def test_scripts_run_from_the_shell(self):
        example = ROOT / "skills" / "record-transcriber" / "assets" / "example-transcription.json"
        r = subprocess.run([sys.executable, str(RT / "transcription_to_gedcom.py"), "validate", str(example)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        r = subprocess.run([sys.executable, str(RT / "transcription_to_gedcom.py"), "date", "18 brumaire an VIII"], capture_output=True, text=True)
        self.assertIn("9 NOV 1799", r.stdout)


if __name__ == "__main__":
    unittest.main()
