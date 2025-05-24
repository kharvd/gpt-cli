import unittest
# Need to adjust import path if tests are run from the root directory
# For now, assuming direct import works or PYTHONPATH is set up
from gptcli.cli import (
    CURRENT_LANGUAGE,
    set_current_language,
    get_text,
    TRANSLATIONS,
    parse_args as cli_parse_args  # Rename to avoid confusion if other parse_args exist
)

class TestCliI18n(unittest.TestCase):

    def setUp(self):
        # Reset language to default before each test
        set_current_language("en")

    def tearDown(self):
        # Ensure language is reset after tests, especially if a test fails
        set_current_language("en")

    def test_default_language_is_english(self):
        self.assertEqual(CURRENT_LANGUAGE, "en")
        # Test a sample string
        expected_prompt = TRANSLATIONS["en"]["PROMPT_INPUT"]
        self.assertEqual(get_text("PROMPT_INPUT"), expected_prompt)

    def test_set_current_language_updates_language_and_get_text(self):
        set_current_language("fr")
        self.assertEqual(CURRENT_LANGUAGE, "fr")
        
        # Test a sample string in French
        expected_prompt_fr = TRANSLATIONS["fr"]["PROMPT_INPUT"]
        self.assertEqual(get_text("PROMPT_INPUT"), expected_prompt_fr)

        # Switch back to English
        set_current_language("en")
        self.assertEqual(CURRENT_LANGUAGE, "en")
        expected_prompt_en = TRANSLATIONS["en"]["PROMPT_INPUT"]
        self.assertEqual(get_text("PROMPT_INPUT"), expected_prompt_en)

    def test_get_text_retrieves_correct_translations(self):
        # English
        set_current_language("en")
        self.assertEqual(get_text("CLEARED_CONVERSATION"), TRANSLATIONS["en"]["CLEARED_CONVERSATION"])
        self.assertEqual(get_text("NOTHING_TO_RERUN"), TRANSLATIONS["en"]["NOTHING_TO_RERUN"])

        # French
        set_current_language("fr")
        self.assertEqual(get_text("CLEARED_CONVERSATION"), TRANSLATIONS["fr"]["CLEARED_CONVERSATION"])
        self.assertEqual(get_text("NOTHING_TO_RERUN"), TRANSLATIONS["fr"]["NOTHING_TO_RERUN"])
        
        # Test with formatting
        set_current_language("en")
        error_msg_en = get_text("GENERIC_ERROR", type_e="TestType", e="TestError")
        self.assertIn("TestType", error_msg_en)
        self.assertIn("TestError", error_msg_en)
        self.assertTrue(error_msg_en.startswith("[red]Error: "))

        set_current_language("fr")
        error_msg_fr = get_text("GENERIC_ERROR", type_e="TestTypeFR", e="TestErrorFR")
        self.assertIn("TestTypeFR", error_msg_fr)
        self.assertIn("TestErrorFR", error_msg_fr)
        self.assertTrue(error_msg_fr.startswith("[red]Erreur : "))


    def test_set_current_language_with_invalid_code_defaults_to_english(self):
        # From default 'en'
        set_current_language("invalid_lang_code")
        self.assertEqual(CURRENT_LANGUAGE, "en")
        self.assertEqual(get_text("PROMPT_INPUT"), TRANSLATIONS["en"]["PROMPT_INPUT"])

        # From 'fr'
        set_current_language("fr")
        self.assertEqual(CURRENT_LANGUAGE, "fr") # Pre-condition
        set_current_language("another_invalid_code")
        self.assertEqual(CURRENT_LANGUAGE, "en")
        self.assertEqual(get_text("PROMPT_INPUT"), TRANSLATIONS["en"]["PROMPT_INPUT"])

    def test_cli_parse_args_switches_language_and_strips_command(self):
        # Switch to French
        prompt, args = cli_parse_args("Hello world --lang fr --model gpt-4")
        self.assertEqual(CURRENT_LANGUAGE, "fr")
        self.assertEqual(prompt, "Hello world") # --lang fr should be stripped
        self.assertEqual(args, {"model": "gpt-4"}) # Other args should remain

        # Check if a CLI message is now in French
        self.assertEqual(get_text("PROMPT_INPUT"), TRANSLATIONS["fr"]["PROMPT_INPUT"])

        # Switch back to English
        prompt, args = cli_parse_args("--lang en This is a test")
        self.assertEqual(CURRENT_LANGUAGE, "en")
        self.assertEqual(prompt, "This is a test") # --lang en should be stripped
        self.assertEqual(args, {})

        # Check if a CLI message is now in English
        self.assertEqual(get_text("PROMPT_INPUT"), TRANSLATIONS["en"]["PROMPT_INPUT"])

    def test_cli_parse_args_with_invalid_lang_code(self):
        set_current_language("fr") # Start in French
        self.assertEqual(CURRENT_LANGUAGE, "fr")

        prompt, args = cli_parse_args("Test --lang invalid --param test")
        # Should default to English
        self.assertEqual(CURRENT_LANGUAGE, "en")
        self.assertEqual(prompt, "Test") # --lang invalid should be stripped
        self.assertEqual(args, {"param": "test"})
        self.assertEqual(get_text("PROMPT_INPUT"), TRANSLATIONS["en"]["PROMPT_INPUT"])

    def test_cli_parse_args_no_lang_does_not_change_language(self):
        set_current_language("fr") # Start in French
        self.assertEqual(CURRENT_LANGUAGE, "fr")

        prompt, args = cli_parse_args("Just a regular prompt --model gpt-3.5")
        self.assertEqual(CURRENT_LANGUAGE, "fr") # Should remain French
        self.assertEqual(prompt, "Just a regular prompt")
        self.assertEqual(args, {"model": "gpt-3.5"})
        self.assertEqual(get_text("PROMPT_INPUT"), TRANSLATIONS["fr"]["PROMPT_INPUT"])

    def test_get_text_fallback_for_missing_key(self):
        # Ensure current language is one that has a specific translation (e.g. fr)
        set_current_language("fr")
        # A key that exists in 'en' but not in 'fr' (hypothetical)
        missing_key_in_fr = "A_KEY_ONLY_IN_EN"
        # Add it to 'en' for the test
        TRANSLATIONS["en"][missing_key_in_fr] = "English specific value"
        
        # If fr is current lang, but key missing, should fallback to en
        self.assertEqual(get_text(missing_key_in_fr), "English specific value")
        
        # Clean up the added key
        del TRANSLATIONS["en"][missing_key_in_fr]

    def test_get_text_fallback_for_completely_missing_key(self):
        # A key that doesn't exist in any language
        non_existent_key = "A_KEY_THAT_DOES_NOT_EXIST"
        self.assertEqual(get_text(non_existent_key), non_existent_key) # Should return the key itself

if __name__ == "__main__":
    unittest.main()
