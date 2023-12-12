from unittest import mock
import httpx

from openai import BadRequestError, OpenAIError

from gptcli.session import ChatSession

system_message = {"role": "system", "content": "system message"}


def setup_assistant_mock():
    assistant_mock = mock.MagicMock()
    assistant_mock.init_messages.return_value = [system_message]
    return assistant_mock


def setup_listener_mock():
    listener_mock = mock.MagicMock()
    response_streamer_mock = mock.MagicMock()
    response_streamer_mock.__enter__.return_value = response_streamer_mock
    listener_mock.response_streamer.return_value = response_streamer_mock
    return listener_mock, response_streamer_mock


def setup_session():
    assistant_mock = setup_assistant_mock()
    listener_mock, _ = setup_listener_mock()
    session = ChatSession(assistant_mock, listener_mock)
    return assistant_mock, listener_mock, session


def test_simple_input():
    assistant_mock, listener_mock, session = setup_session()

    expected_response = "assistant message"
    assistant_mock.complete_chat.return_value = [expected_response]

    user_input = "user message"
    should_continue = session.process_input(user_input, {})
    assert should_continue

    user_message = {"role": "user", "content": user_input}
    assistant_message = {"role": "assistant", "content": expected_response}

    assistant_mock.complete_chat.assert_called_once_with(
        [system_message, user_message], override_params={}
    )
    listener_mock.on_chat_message.assert_has_calls(
        [mock.call(user_message), mock.call(assistant_message)]
    )


def test_quit():
    _, _, session = setup_session()
    should_continue = session.process_input(":q", {})
    assert not should_continue


def test_clear():
    assistant_mock, listener_mock, session = setup_session()

    assistant_mock.init_messages.assert_called_once()
    assistant_mock.init_messages.reset_mock()

    assistant_mock.complete_chat.return_value = ["assistant_message"]

    should_continue = session.process_input("user_message", {})
    assert should_continue

    assistant_mock.complete_chat.assert_called_once_with(
        [system_message, {"role": "user", "content": "user_message"}],
        override_params={},
    )
    listener_mock.on_chat_message.assert_has_calls(
        [
            mock.call({"role": "user", "content": "user_message"}),
            mock.call({"role": "assistant", "content": "assistant_message"}),
        ]
    )
    assistant_mock.complete_chat.reset_mock()
    listener_mock.on_chat_message.reset_mock()

    should_continue = session.process_input(":c", {})
    assert should_continue

    assistant_mock.init_messages.assert_called_once()
    listener_mock.on_chat_clear.assert_called_once()
    assistant_mock.complete_chat.assert_not_called()

    assistant_mock.complete_chat.return_value = ["assistant_message_1"]

    should_continue = session.process_input("user_message_1", {})
    assert should_continue

    assistant_mock.complete_chat.assert_called_once_with(
        [system_message, {"role": "user", "content": "user_message_1"}],
        override_params={},
    )
    listener_mock.on_chat_message.assert_has_calls(
        [
            mock.call({"role": "user", "content": "user_message_1"}),
            mock.call({"role": "assistant", "content": "assistant_message_1"}),
        ]
    )


def test_rerun():
    assistant_mock, listener_mock, session = setup_session()

    assistant_mock.init_messages.assert_called_once()
    assistant_mock.init_messages.reset_mock()

    # Re-run before any input shouldn't do anything
    should_continue = session.process_input(":r", {})
    assert should_continue

    assistant_mock.init_messages.assert_not_called()
    assistant_mock.complete_chat.assert_not_called()
    listener_mock.on_chat_message.assert_not_called()
    listener_mock.on_chat_rerun.assert_called_once_with(False)

    listener_mock.on_chat_rerun.reset_mock()

    # Now proper re-run
    assistant_mock.complete_chat.return_value = ["assistant_message"]

    should_continue = session.process_input("user_message", {})
    assert should_continue

    assistant_mock.complete_chat.assert_called_once_with(
        [system_message, {"role": "user", "content": "user_message"}],
        override_params={},
    )
    listener_mock.on_chat_message.assert_has_calls(
        [
            mock.call({"role": "user", "content": "user_message"}),
            mock.call({"role": "assistant", "content": "assistant_message"}),
        ]
    )
    assistant_mock.complete_chat.reset_mock()
    listener_mock.on_chat_message.reset_mock()

    assistant_mock.complete_chat.return_value = ["assistant_message_1"]

    should_continue = session.process_input(":r", {})
    assert should_continue

    listener_mock.on_chat_rerun.assert_called_once_with(True)

    assistant_mock.complete_chat.assert_called_once_with(
        [system_message, {"role": "user", "content": "user_message"}],
        override_params={},
    )
    listener_mock.on_chat_message.assert_has_calls(
        [
            mock.call({"role": "assistant", "content": "assistant_message_1"}),
        ]
    )


def test_args():
    assistant_mock, listener_mock, session = setup_session()

    assistant_mock.supported_overrides.return_value = ["arg1"]

    expected_response = "assistant message"
    assistant_mock.complete_chat.return_value = [expected_response]

    user_input = "user message"
    should_continue = session.process_input(user_input, {"arg1": "value1"})
    assert should_continue

    user_message = {"role": "user", "content": user_input}
    assistant_message = {"role": "assistant", "content": expected_response}

    assistant_mock.complete_chat.assert_called_once_with(
        [system_message, user_message], override_params={"arg1": "value1"}
    )
    listener_mock.on_chat_message.assert_has_calls(
        [mock.call(user_message), mock.call(assistant_message)]
    )

    # Now test that rerun reruns with the same args
    assistant_mock.complete_chat.reset_mock()
    listener_mock.on_chat_message.reset_mock()

    assistant_mock.complete_chat.return_value = [expected_response]

    should_continue = session.process_input(":r", {})
    assert should_continue

    assistant_mock.complete_chat.assert_called_once_with(
        [system_message, user_message], override_params={"arg1": "value1"}
    )
    listener_mock.on_chat_message.assert_has_calls([mock.call(assistant_message)])


def test_invalid_request_error():
    assistant_mock, listener_mock, session = setup_session()

    error = BadRequestError(
        "error message",
        response=httpx.Response(
            401, request=httpx.Request("POST", "http://localhost/")
        ),
        body=None,
    )
    assistant_mock.complete_chat.side_effect = error

    user_input = "user message"
    should_continue = session.process_input(user_input, {})
    assert should_continue

    user_message = {"role": "user", "content": user_input}
    listener_mock.on_chat_message.assert_has_calls([mock.call(user_message)])
    listener_mock.on_error.assert_called_once_with(error)

    # Now rerun shouldn't do anything because user input was not saved
    assistant_mock.complete_chat.reset_mock()
    listener_mock.on_chat_message.reset_mock()
    listener_mock.on_error.reset_mock()

    should_continue = session.process_input(":r", {})
    assert should_continue

    assistant_mock.complete_chat.assert_not_called()
    listener_mock.on_chat_message.assert_not_called()
    listener_mock.on_error.assert_not_called()
    listener_mock.on_chat_rerun.assert_called_once_with(False)


class OpenAITestError(OpenAIError):
    pass


def test_openai_error():
    assistant_mock, listener_mock, session = setup_session()

    error = OpenAITestError()
    assistant_mock.complete_chat.side_effect = error

    user_input = "user message"
    should_continue = session.process_input(user_input, {})
    assert should_continue

    user_message = {"role": "user", "content": user_input}
    listener_mock.on_chat_message.assert_has_calls([mock.call(user_message)])
    listener_mock.on_error.assert_called_once_with(error)

    # Re-run should work
    assistant_mock.complete_chat.reset_mock()
    listener_mock.on_chat_message.reset_mock()
    listener_mock.on_error.reset_mock()

    assistant_mock.complete_chat.side_effect = None
    assistant_mock.complete_chat.return_value = ["assistant message"]

    should_continue = session.process_input(":r", {})
    assert should_continue

    assistant_mock.complete_chat.assert_called_once_with(
        [system_message, user_message], override_params={}
    )
    listener_mock.on_chat_message.assert_has_calls(
        [
            mock.call({"role": "assistant", "content": "assistant message"}),
        ]
    )


def test_stream():
    assistant_mock, listener_mock, session = setup_session()
    assistant_message = "assistant message"
    assistant_mock.complete_chat.return_value = list(assistant_message)

    response_streamer_mock = listener_mock.response_streamer.return_value

    session.process_input("user message", {})

    response_streamer_mock.assert_has_calls(
        [mock.call.on_next_token(token) for token in assistant_message]
    )
