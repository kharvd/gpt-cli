import unittest
from unittest import mock
import sys
import logging
import os
import yaml # For creating dummy_config.yml

# Make sure gptcli is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import gptcli.gpt
from gptcli.config import GptCliConfig, read_yaml_config, CONFIG_FILE_PATHS


# Disable logging for tests unless explicitly enabled
logging.disable(logging.CRITICAL)

class TestGptMain(unittest.TestCase):

    def tearDown(self):
        # Clean up any dummy files created
        if os.path.exists("dummy_config.yml"):
            os.remove("dummy_config.yml")

    @mock.patch.dict(os.environ, {}, clear=True)
    @mock.patch('sys.exit')
    @mock.patch('builtins.print')
    @mock.patch('gptcli.config.choose_config_file', return_value="")
    def test_missing_api_key_message(self, mock_choose_config, mock_print, mock_exit):
        """Test that the correct error message is printed when no API key is found."""
        gptcli.gpt.main()
        mock_exit.assert_called_once_with(1)
        expected_message_parts = [
            "OpenAI API key is missing.",
            "OPENAI_API_KEY environment variable",
            "api_key: <your_key>",
            "openai_api_key: <your_key>",
            "~/.config/gpt-cli/gpt.yml",
            "~/.gptrc",
        ]
        call_args_list = mock_print.call_args_list
        self.assertTrue(len(call_args_list) > 0, "print was not called")
        printed_message = call_args_list[0][0][0] # Get the first argument of the first call
        for part in expected_message_parts:
            self.assertIn(part, printed_message)

    @mock.patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}, clear=True)
    @mock.patch('gptcli.gpt.logger.info') # Mocking the logger instance used in gpt.py
    @mock.patch('gptcli.gpt.init_assistant') # Avoid complex assistant initialization
    @mock.patch('gptcli.gpt.run_interactive') # Avoid starting interactive session
    def test_logging_with_config_file(self, mock_run_interactive, mock_init_assistant, mock_logger_info):
        """Test that loading a config file is logged."""
        dummy_config_path = "dummy_config.yml"
        with open(dummy_config_path, "w") as f:
            yaml.dump({"default_assistant": "test"}, f)

        with mock.patch('gptcli.config.choose_config_file', return_value=dummy_config_path):
            # We need to mock read_yaml_config because the dummy file might not have all necessary fields
            # for a full GptCliConfig object, or the test environment might not have access to it in the same way.
            # Returning a default GptCliConfig is sufficient for this logging test.
            with mock.patch('gptcli.gpt.read_yaml_config', return_value=GptCliConfig()) as mock_read_yaml:
                gptcli.gpt.main()

        mock_logger_info.assert_any_call(f"Using configuration file: {dummy_config_path}")

        if os.path.exists(dummy_config_path):
            os.remove(dummy_config_path)

    @mock.patch.dict(os.environ, {"OPENAI_API_KEY": "test_key"}, clear=True)
    @mock.patch('gptcli.gpt.logger.info') # Mocking the logger instance used in gpt.py
    @mock.patch('gptcli.config.choose_config_file', return_value="")
    @mock.patch('gptcli.gpt.init_assistant') # Avoid complex assistant initialization
    @mock.patch('gptcli.gpt.run_interactive') # Avoid starting interactive session
    def test_logging_no_config_file(self, mock_run_interactive, mock_init_assistant, mock_choose_config, mock_logger_info):
        """Test that not finding a config file is logged."""
        gptcli.gpt.main()
        # The mock_choose_config is passed as an argument due to the order of decorators,
        # but it's the mock_logger_info we are interested in here.
        # We need to get the correct mock object.
        actual_logger_mock = mock_choose_config # This is actually mock_logger_info due to decorator order
        if not isinstance(actual_logger_mock, mock.MagicMock): # If it's not a mock, find the right one
             actual_logger_mock = mock_logger_info

        actual_logger_mock.assert_any_call("No configuration file found. Using default settings and environment variables.")

if __name__ == '__main__':
    unittest.main()
