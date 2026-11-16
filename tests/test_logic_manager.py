import os
import re
import unittest
from datetime import datetime

from LogicManager import (EligibilityRule, JobRequirements, LogicManager, OutcomeRule,
                           OutcomeRuleFactory, ScoreCalculator, ScoreBreakdown, ScoreOnlyRule,
                           ScoringPolicy)
from Models import Outcome, ResumeData
from tests.helpers import (NO_SKILLS_REQUIRED, REQUIREMENTS, SAMPLE_BORDERLINE, SAMPLE_NON_IT,
                           SAMPLE_STRONG, SAMPLE_WEAK, make_resume, resume, write_temp_file)


"""
Skill requirements is set to 0, so that other factors can be checked.
"""
NOTHING_MATCHES = JobRequirements(["zzz-unmatched-skill"], min_experience=0)


def score_of(data, requirements=NO_SKILLS_REQUIRED):
    return ScoreCalculator().calculate(data, requirements).score


class JobRequirementsTests(unittest.TestCase):
    def read(self, text):
        path = write_temp_file(text)
        self.addCleanup(os.remove, path)
        return JobRequirements.from_file(path)

    def test_reads_values(self):
        req = self.read("required_skills: python, sql ,git\nmin_experience: 2.5\noutcome_rule: score_only\n")
        self.assertEqual(req.required_skills, ["python", "sql", "git"])
        self.assertEqual(req.min_experience, 2.5)
        self.assertEqual(req.outcome_rule, "score_only")

    def test_ignores_comments_and_blank_lines(self):
        req = self.read("# comment\n\nrequired_skills: python\n# min_experience: 9\n")
        self.assertEqual(req.required_skills, ["python"])
        self.assertEqual(req.min_experience, 0.0)

    def test_missing_file_gives_defaults(self):
        req = JobRequirements.from_file("/no/such/requirements.txt")
        self.assertEqual(req.required_skills, [])
        self.assertEqual(req.min_experience, 0.0)
        self.assertEqual(req.outcome_rule, JobRequirements.DEFAULT_RULE)

    def test_bad_min_experience_keeps_default(self):
        req = self.read("required_skills: python\nmin_experience: lots\n")
        self.assertEqual(req.min_experience, 0.0)
        self.assertEqual(req.required_skills, ["python"])

    def test_default_rule_is_multi_condition(self):
        self.assertEqual(self.read("required_skills: python\n").outcome_rule, "multi_condition")

    def test_properties_return_copies(self):
        req = JobRequirements(["python"], 1)
        req.required_skills.append("hacked")
        self.assertEqual(req.required_skills, ["python"])


class ScoreCalculatorTests(unittest.TestCase):
    def test_lowercase_certificates(self):
        out = ScoreCalculator.lowercase_certificates({" IT ": [" AWS CCP ", "CKA"]})
        self.assertEqual(out, {"it": ["aws ccp", "cka"]})

    def test_lowercase_certificates_none_and_empty(self):
        self.assertEqual(ScoreCalculator.lowercase_certificates(None), {})
        self.assertEqual(ScoreCalculator.lowercase_certificates({}), {})

    def test_skill_exact_and_substring_match(self):
        self.assertTrue(ScoreCalculator.has_skill("python", ["python"]))
        self.assertTrue(ScoreCalculator.has_skill("sql", ["sql (postgresql, mysql)"]))
        self.assertFalse(ScoreCalculator.has_skill("docker", ["python", "sql"]))
        self.assertFalse(ScoreCalculator.has_skill("python", []))

    def test_full_marks(self):
        self.assertEqual(score_of(resume(SAMPLE_STRONG), REQUIREMENTS), 10.0)

    def test_skills_are_capped_at_four(self):
        four = make_resume(0, 0, ["python", "sql", "tableau", "aws"])
        six = make_resume(0, 0, ["python", "sql", "tableau", "aws", "git", "linux"])
        self.assertEqual(score_of(four, REQUIREMENTS), 4.0)
        self.assertEqual(score_of(six, REQUIREMENTS), 4.0)

    def test_three_skills_is_three_quarters_of_the_skill_portion(self):
        self.assertEqual(score_of(make_resume(0, 0, ["python", "sql", "tableau"]), REQUIREMENTS), 3.0)

    def test_experience_scale(self):
        for years, expected in [(0, 0.0), (1, 0.8), (2.5, 2.0), (5, 4.0), (20, 4.0)]:
            self.assertEqual(score_of(make_resume(years), NOTHING_MATCHES), expected, f"{years} years")

    def test_certificate_scale(self):
        for certs, expected in [(0, 0.0), (1, 0.7), (2, 1.3), (3, 2.0), (9, 2.0)]:
            self.assertEqual(score_of(make_resume(0, certs), NOTHING_MATCHES), expected, f"{certs} certs")

    def test_no_required_skills_gives_full_skill_marks(self):
        self.assertEqual(score_of(make_resume(0, 0)), 4.0)

    def test_only_the_it_field_counts(self):
        data = ResumeData("x.pdf", "x", [], {"IT": 2, "Healthcare": 10}, {"Healthcare": ["BLS"]})
        breakdown = ScoreCalculator().calculate(data, NO_SKILLS_REQUIRED)
        self.assertEqual(breakdown.it_experience_years, 2)
        self.assertEqual(breakdown.it_certs, [])

    def test_breakdown_reports_missing_skills_and_lowercase_certs(self):
        breakdown = ScoreCalculator().calculate(resume(SAMPLE_BORDERLINE), REQUIREMENTS)
        self.assertEqual(len(breakdown.missing_skills), 6)
        self.assertEqual(breakdown.it_certs, ["tableau desktop specialist", "aws cloud practitioner"])
        self.assertIsInstance(breakdown, ScoreBreakdown)

    def test_policy_changes_the_score_without_editing_the_calculator(self):
        generous = ScoringPolicy(experience_for_full_score=2)
        calc = ScoreCalculator(generous)
        self.assertEqual(calc.calculate(make_resume(2), NO_SKILLS_REQUIRED).score, 8.0)


class OutcomeRuleTests(unittest.TestCase):
    def breakdown(self, score, years=5.0):
        return ScoreBreakdown(score=score, it_experience_years=years)

    def test_abstract_rule_cannot_be_created(self):
        with self.assertRaises(TypeError):
            OutcomeRule()

    def test_rules_have_names(self):
        self.assertEqual(ScoreOnlyRule().name, "score_only")
        self.assertEqual(EligibilityRule().name, "multi_condition")

    def test_boundaries_for_every_rule(self):
        req = JobRequirements([], min_experience=0)
        for rule in (ScoreOnlyRule(), EligibilityRule()):
            with self.subTest(rule=rule.name):
                self.assertIs(rule.decide(self.breakdown(10.0), req), Outcome.ACCEPTED)
                self.assertIs(rule.decide(self.breakdown(7.6), req), Outcome.ACCEPTED)
                self.assertIs(rule.decide(self.breakdown(7.5), req), Outcome.FLAGGED)
                self.assertIs(rule.decide(self.breakdown(4.1), req), Outcome.FLAGGED)
                self.assertIs(rule.decide(self.breakdown(4.0), req), Outcome.REJECTED)
                self.assertIs(rule.decide(self.breakdown(0.0), req), Outcome.REJECTED)

    def test_score_only_ignores_experience(self):
        req = JobRequirements([], min_experience=10)
        self.assertIs(ScoreOnlyRule().decide(self.breakdown(9.0, years=1), req), Outcome.ACCEPTED)

    def test_multi_condition_needs_the_minimum_experience(self):
        req = JobRequirements([], min_experience=5)
        rule = EligibilityRule()
        self.assertIs(rule.decide(self.breakdown(9.0, years=4), req), Outcome.FLAGGED)
        self.assertIs(rule.decide(self.breakdown(9.0, years=5), req), Outcome.ACCEPTED)

    def test_multi_condition_still_rejects_low_scores(self):
        req = JobRequirements([], min_experience=5)
        self.assertIs(EligibilityRule().decide(self.breakdown(3.0, years=9), req), Outcome.REJECTED)

    def test_subclass_can_be_used_where_the_base_rule_is_expected(self):
        req = JobRequirements([], min_experience=0)
        self.assertIsInstance(EligibilityRule(), ScoreOnlyRule)
        self.assertIs(EligibilityRule().decide(self.breakdown(4.0), req), Outcome.REJECTED)


class OutcomeRuleFactoryTests(unittest.TestCase):
    def test_creates_known_rules(self):
        self.assertIsInstance(OutcomeRuleFactory.create("score_only"), ScoreOnlyRule)
        self.assertIsInstance(OutcomeRuleFactory.create("multi_condition"), EligibilityRule)

    def test_unknown_name_falls_back_to_the_default(self):
        self.assertIsInstance(OutcomeRuleFactory.create("nonsense"), EligibilityRule)

    def test_new_rules_can_be_registered_without_editing_existing_code(self):
        class AlwaysFlag(OutcomeRule):
            @property
            def name(self):
                return "always_flag"

            def _qualifies_for_accept(self, breakdown, requirements):
                return False

        OutcomeRuleFactory.register("always_flag", AlwaysFlag)
        self.addCleanup(OutcomeRuleFactory._rules.pop, "always_flag")
        manager = LogicManager(requirements=JobRequirements([], 0, "always_flag"))
        self.assertIs(manager.evaluate_resume(resume(SAMPLE_STRONG)).outcome, Outcome.FLAGGED)
        self.assertIn("always_flag", OutcomeRuleFactory.available())


class LogicManagerTests(unittest.TestCase):
    def manager(self, requirements=REQUIREMENTS, **kwargs):
        return LogicManager(requirements=requirements, **kwargs)

    def test_accepted(self):
        record = self.manager().evaluate_resume(resume(SAMPLE_STRONG))
        self.assertEqual((record.name, record.score, record.outcome), ("Arthur Goatson", 10.0, Outcome.ACCEPTED))

    def test_borderline_is_flagged_at_exactly_the_threshold(self):
        record = self.manager().evaluate_resume(resume(SAMPLE_BORDERLINE))
        self.assertEqual(record.score, 7.5)
        self.assertIs(record.outcome, Outcome.FLAGGED)

    def test_weak_and_non_it_are_rejected(self):
        manager = self.manager()
        self.assertIs(manager.evaluate_resume(resume(SAMPLE_WEAK)).outcome, Outcome.REJECTED)
        self.assertIs(manager.evaluate_resume(resume(SAMPLE_NON_IT)).outcome, Outcome.REJECTED)

    def test_few_skills_but_high_score_is_still_accepted(self):
        """
        Tests for a few skills (2/9), but score is high enough to be accepted.
        """
        record = self.manager().evaluate_resume(make_resume(5, 3, ["python", "sql"]))
        self.assertEqual(record.score, 8.0)
        self.assertIs(record.outcome, Outcome.ACCEPTED)

    def test_multi_condition_default_flags_high_score_with_too_little_experience(self):
        req = JobRequirements(REQUIREMENTS.required_skills, min_experience=5)
        data = make_resume(4, 3, ["python", "sql", "tableau", "aws"])
        self.assertIs(self.manager(req).evaluate_resume(data).outcome, Outcome.FLAGGED)

    def test_score_only_rule_accepts_the_same_resume(self):
        req = JobRequirements(REQUIREMENTS.required_skills, min_experience=5, outcome_rule="score_only")
        data = make_resume(4, 3, ["python", "sql", "tableau", "aws"])
        self.assertIs(self.manager(req).evaluate_resume(data).outcome, Outcome.ACCEPTED)

    def test_record_fields(self):
        record = self.manager().evaluate_resume(resume(SAMPLE_STRONG))
        self.assertEqual(record.it_experience_years, 5)
        self.assertEqual(record.missing_skills_count, 3)
        self.assertIn("python", record.skills)
        self.assertEqual(record.it_certs[0], "aws certified solutions architect")
        self.assertEqual(set(record.certificates), {"it", "fnb"})
        self.assertIsNone(record.id)

    def test_timestamp_comes_from_the_injected_clock(self):
        fixed = datetime(2026, 3, 4, 5, 6, 7)
        record = self.manager(clock=lambda: fixed).evaluate_resume(resume(SAMPLE_WEAK))
        self.assertEqual(record.timestamp, "2026-03-04 05:06:07")

    def test_default_clock_format(self):
        record = self.manager().evaluate_resume(resume(SAMPLE_WEAK))
        self.assertRegex(record.timestamp, r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")

    def test_missing_name_becomes_unknown(self):
        data = ResumeData("x.pdf", "", [], {}, {})
        self.assertEqual(self.manager().evaluate_resume(data).name, "Unknown")

    def test_empty_resume_does_not_crash(self):
        record = self.manager().evaluate_resume(ResumeData("x.pdf", "A", [], {}, {}))
        self.assertEqual(record.score, 0.0)
        self.assertIs(record.outcome, Outcome.REJECTED)

    def test_batch_keeps_order(self):
        from Models import ResumeBatch
        batch = ResumeBatch(resume(s) for s in (SAMPLE_STRONG, SAMPLE_BORDERLINE, SAMPLE_WEAK, SAMPLE_NON_IT))
        results = self.manager().evaluate_batch(batch)
        self.assertEqual([r.outcome for r in results],
                         [Outcome.ACCEPTED, Outcome.FLAGGED, Outcome.REJECTED, Outcome.REJECTED])

    def test_empty_batch(self):
        from Models import ResumeBatch
        self.assertEqual(self.manager().evaluate_batch(ResumeBatch()), [])

    def test_requirements_file_is_re_read_for_every_batch(self):
        from Models import ResumeBatch
        path = write_temp_file("required_skills: python\nmin_experience: 0\n")
        self.addCleanup(os.remove, path)
        manager = LogicManager(requirements_path=path)
        batch = ResumeBatch([make_resume(0, 0, ["python"])])
        self.assertEqual(manager.evaluate_batch(batch)[0].missing_skills_count, 0)
        with open(path, "w", encoding="utf-8") as f:
            f.write("required_skills: python, docker\n")
        self.assertEqual(manager.evaluate_batch(batch)[0].missing_skills_count, 1)


if __name__ == "__main__":
    unittest.main()
