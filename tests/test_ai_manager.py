"""Tests for ai_manager.py. A fake client stands in for Gemini, so no API or key is needed."""

import json
import os
import sys
import types
import unittest

from AIManager import (AIClient, AIConfigurationError, AIManager, GeminiClient,
                        NoResumesUploadedError, ResponseValidator, build_prompt, load_env_file)
from Models import ResumeBatch
from tests.helpers import FakeAIClient, SAMPLE_BORDERLINE, SAMPLE_STRONG, write_temp_file


def reply(*samples):
    return json.dumps(list(samples))

#Checks that the validator takes in the good records and reject the bad ones
class ResponseValidatorTests(unittest.TestCase):
    def setUp(self):
        #create a new validator for each test
        self.v = ResponseValidator()

    def test_valid_record(self):
        #if the record is correct it passes
        self.assertTrue(self.v.is_valid(SAMPLE_STRONG))

    def test_missing_field_is_invalid(self):
        #test if removing one of the five field we need makes the record invalid
        for key in ResponseValidator.REQUIRED_FIELDS:
            bad = {k: v for k, v in SAMPLE_STRONG.items() if k != key}
            self.assertFalse(self.v.is_valid(bad), key)

    def test_wrong_types_are_invalid(self):
        #test to see if a wrong type is entered will it be rejected
        cases = {
            "name": 123,
            "filename": None,
            "skills": "python, sql",
            "experience_by_field": [("IT", 3)],
            "certificates_by_industry": ["AWS"],
        }
        for key, value in cases.items():
            self.assertFalse(self.v.is_valid({**SAMPLE_STRONG, key: value}), key)

    def test_text_years_are_invalid(self):
        self.assertFalse(self.v.is_valid({**SAMPLE_STRONG, "experience_by_field": {"IT": "four years"}}))

    def test_skill_items_must_be_text(self):
        self.assertFalse(self.v.is_valid({**SAMPLE_STRONG, "skills": ["python", 5]}))

    def test_certificates_must_be_lists_of_text(self):
        self.assertFalse(self.v.is_valid({**SAMPLE_STRONG, "certificates_by_industry": {"IT": "AWS"}}))
        self.assertFalse(self.v.is_valid({**SAMPLE_STRONG, "certificates_by_industry": {"IT": [1]}}))

    def test_not_a_dict_is_invalid(self):
        for value in (None, "text", 5, ["a"]):
            self.assertFalse(self.v.is_valid(value))

    def test_empty_collections_are_valid(self):
        self.assertTrue(self.v.is_valid({**SAMPLE_STRONG, "skills": [], "experience_by_field": {},
                                         "certificates_by_industry": {}}))

    def test_parse_plain_json_list(self):
        self.assertEqual(len(self.v.parse(reply(SAMPLE_STRONG))), 1)

    def test_parse_strips_markdown_fence(self):
        self.assertEqual(len(self.v.parse("```json\n" + reply(SAMPLE_STRONG) + "\n```")), 1)

    def test_parse_rejects_bad_json_and_non_lists(self):
        self.assertIsNone(self.v.parse("not json"))
        self.assertIsNone(self.v.parse(""))
        self.assertIsNone(self.v.parse('{"a": 1}'))
        self.assertIsNone(self.v.parse(None))

    def test_valid_records_counts_dropped(self):
        valid, dropped = self.v.valid_records([SAMPLE_STRONG, {"name": "x"}, SAMPLE_BORDERLINE])
        self.assertEqual((len(valid), dropped), (2, 1))


class BuildPromptTests(unittest.TestCase):
    def test_prompt_lists_files_and_demands_json(self):
        prompt = build_prompt(["a.pdf", "b.pdf"])
        self.assertIn("2 resumes", prompt)
        self.assertIn("- a.pdf", prompt)
        self.assertIn("- b.pdf", prompt)
        self.assertIn("JSON", prompt)

    def test_prompt_asks_for_the_five_fields_and_the_it_label(self):
        prompt = build_prompt(["a.pdf"])
        for key in ResponseValidator.REQUIRED_FIELDS:
            self.assertIn(key, prompt)
        self.assertIn('"IT"', prompt)

    def test_prompt_never_mentions_job_requirements(self):
        self.assertNotIn("required_skills", build_prompt(["a.pdf"]))


class AIManagerTests(unittest.TestCase):
    def manager(self, replies, **kwargs):
        self.sleeps = []
        self.client = FakeAIClient(replies)
        return AIManager(self.client, sleep=self.sleeps.append, **kwargs)

    PATHS = ["resumes/a.pdf", "resumes/b.pdf"]

    def test_returns_a_batch_of_validated_resumes(self):
        batch = self.manager([reply(SAMPLE_STRONG, SAMPLE_BORDERLINE)]).process_resume_batch(self.PATHS)
        self.assertIsInstance(batch, ResumeBatch)
        self.assertEqual([r.name for r in batch], ["Arthur Goatson", "Priya Sharma"])
        self.assertEqual(batch.filenames, ["arthur_goatson.pdf", "priya_sharma.pdf"])

    def test_sends_one_request_for_the_whole_batch(self):
        manager = self.manager([reply(SAMPLE_STRONG)])
        manager.process_resume_batch(self.PATHS)
        self.assertEqual(len(self.client.calls), 1)
        prompt, paths = self.client.calls[0]
        self.assertEqual(paths, self.PATHS)
        self.assertIn("- a.pdf", prompt)

    def test_no_paths_means_no_api_call(self):
        manager = self.manager([])
        self.assertTrue(manager.process_resume_batch([]).is_empty())
        self.assertEqual(self.client.calls, [])

    def test_malformed_json_is_retried_without_waiting(self):
        batch = self.manager(["garbage", reply(SAMPLE_STRONG)]).process_resume_batch(self.PATHS)
        self.assertEqual(len(batch), 1)
        self.assertEqual(len(self.client.calls), 2)
        self.assertEqual(self.sleeps, [])

    def test_reply_with_no_valid_records_is_retried(self):
        batch = self.manager([reply({"name": "x"}), reply(SAMPLE_STRONG)]).process_resume_batch(self.PATHS)
        self.assertEqual(len(batch), 1)
        self.assertEqual(len(self.client.calls), 2)

    def test_invalid_records_are_dropped_but_valid_ones_kept(self):
        batch = self.manager([reply(SAMPLE_STRONG, {"name": "broken"})]).process_resume_batch(self.PATHS)
        self.assertEqual([r.name for r in batch], ["Arthur Goatson"])
        self.assertEqual(len(self.client.calls), 1)

    def test_api_errors_are_retried_with_a_growing_wait(self):
        errors = [ConnectionError("down"), TimeoutError("slow")]
        batch = self.manager(errors + [reply(SAMPLE_STRONG)]).process_resume_batch(self.PATHS)
        self.assertEqual(len(batch), 1)
        self.assertEqual(self.sleeps, [5, 10])

    def test_gives_up_after_the_maximum_attempts(self):
        manager = self.manager([ConnectionError("down")] * 5)
        self.assertTrue(manager.process_resume_batch(self.PATHS).is_empty())
        self.assertEqual(len(self.client.calls), 5)
        self.assertEqual(self.sleeps, [5, 10, 15, 20])   # no pointless wait after the last attempt

    def test_gives_up_when_every_reply_is_malformed(self):
        manager = self.manager(["bad"] * 3, max_retries=3)
        self.assertTrue(manager.process_resume_batch(self.PATHS).is_empty())
        self.assertEqual(len(self.client.calls), 3)

    def test_configuration_errors_are_not_retried(self):
        manager = self.manager([AIConfigurationError("no key")])
        with self.assertRaises(AIConfigurationError):
            manager.process_resume_batch(self.PATHS)
        self.assertEqual(len(self.client.calls), 1)

    def test_nothing_uploaded_returns_empty_without_retrying(self):
        manager = self.manager([NoResumesUploadedError("none")])
        self.assertTrue(manager.process_resume_batch(self.PATHS).is_empty())
        self.assertEqual(len(self.client.calls), 1)

    def test_fake_client_satisfies_the_interface(self):
        self.assertIsInstance(FakeAIClient([]), AIClient)

    def test_interface_cannot_be_instantiated(self):
        with self.assertRaises(TypeError):
            AIClient()


class GeminiClientTests(unittest.TestCase):
    def test_missing_key_raises_a_clear_error_and_never_needs_the_sdk(self):
        saved = os.environ.pop("GEMINI_API_KEY", None)
        self.addCleanup(lambda: saved and os.environ.__setitem__("GEMINI_API_KEY", saved))
        with self.assertRaises(AIConfigurationError) as ctx:
            GeminiClient().generate_json("prompt", ["a.pdf"])
        self.assertIn("GEMINI_API_KEY", str(ctx.exception))

    def test_creating_the_client_needs_no_key(self):
        GeminiClient()   # must not raise: the key is only needed on first use


class GeminiTimeoutTests(unittest.TestCase):
    #Uses stand-ins for the google SDK, so no package, key or network is needed

    def install_fake_sdk(self, with_http_options):
        created = {}

        class Client:
            def __init__(self, api_key, http_options=None):
                created["api_key"], created["http_options"] = api_key, http_options

        genai = types.ModuleType("google.genai")
        genai.Client = Client
        genai_types = types.ModuleType("google.genai.types")
        if with_http_options:
            genai_types.HttpOptions = lambda timeout: ("HttpOptions", timeout)
        genai.types = genai_types
        google = types.ModuleType("google")
        google.genai = genai
        saved = {k: sys.modules.get(k) for k in ("google", "google.genai", "google.genai.types")}
        sys.modules.update({"google": google, "google.genai": genai, "google.genai.types": genai_types})

        def restore():
            for key, value in saved.items():
                if value is None:
                    sys.modules.pop(key, None)
                else:
                    sys.modules[key] = value
        self.addCleanup(restore)
        return created

    def test_requests_get_a_timeout_in_milliseconds(self):
        created = self.install_fake_sdk(with_http_options=True)
        GeminiClient(api_key="k", timeout_seconds=30).get_client()
        self.assertEqual(created["http_options"], ("HttpOptions", 30000))

    def test_older_sdk_without_timeout_support_still_works(self):
        created = self.install_fake_sdk(with_http_options=False)
        GeminiClient(api_key="k").get_client()
        self.assertEqual(created["api_key"], "k")
        self.assertIsNone(created["http_options"])


class LoadEnvFileTests(unittest.TestCase):
    def test_loads_values_and_skips_comments(self):
        path = write_temp_file('# comment\nGEMINI_API_KEY="abc123"\n\nOTHER=\'x y\'\nbadline\n')
        self.addCleanup(os.remove, path)
        env = {}
        load_env_file(path, env)
        self.assertEqual(env, {"GEMINI_API_KEY": "abc123", "OTHER": "x y"})

    def test_existing_variables_win(self):
        path = write_temp_file("GEMINI_API_KEY=from_file\n")
        self.addCleanup(os.remove, path)
        env = {"GEMINI_API_KEY": "from_docker"}
        load_env_file(path, env)
        self.assertEqual(env["GEMINI_API_KEY"], "from_docker")

    def test_missing_file_is_fine(self):
        env = {}
        load_env_file("/no/such/.env", env)
        self.assertEqual(env, {})


if __name__ == "__main__":
    unittest.main()
