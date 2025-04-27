"""Define a hook to help the agent scaffold mitigate repetitive actions or terminate
agent runs early.
"""

import re
import shlex

from jinja2 import Template

from sweagent.agent.hooks.abstract import AbstractAgentHook
from sweagent.agent.hooks.config import RepeatActionMitigatorConfig
from sweagent.exceptions import BlockedActionError, RepetitiveActionExit
from sweagent.types import StepOutput
from sweagent.utils.log import get_logger


def _split_shell_commands(cmd_string: str) -> list[str]:
    """See `split_shell_commands`"""
    # First, tokenize the entire string properly with shlex
    lexer = shlex.shlex(cmd_string, posix=True)
    lexer.whitespace_split = True
    tokens = list(lexer)

    # Now find the command boundaries (&&, ;) while respecting shell syntax
    commands = []
    current_command = []

    for token in tokens:
        if token in ("&&", ";"):
            if current_command:
                commands.append(" ".join(current_command))
                current_command = []
        else:
            current_command.append(token)

    # Don't forget the last command
    if current_command:
        commands.append(" ".join(current_command))

    return commands


def split_shell_commands(cmd_string: str) -> list[str]:
    """Split a shell command string into a list of commands.

    Args:
        cmd_string: Shell command string
    Returns:
        List of commands
    """
    try:
        return _split_shell_commands(cmd_string)
    except ValueError:
        # Fall back
        return cmd_string.split("&&")


def strip_environment_variables(action: str) -> str:
    """Remove environment variable settings from the beginning of a command.

    For example, if the action is `PYTHONPATH=/path FOO=bar command`, return just `command`.
    """
    pattern = r"^\s*(?:[A-Z_]+=[^ ]+\s*)+\s*"
    match = re.match(pattern, action)
    if match:
        return action[match.end() :]
    return action


def get_base_command(action: str) -> str:
    """An action can be multiple shell commands separated by && or ;
    or there might be leading environment variable settings etc.
    In addition, the command might have various arguments

    This function attempts to return the command that is being run
    so that we can categorize the action correctly.

    For example, `cd x/y/z && str_replace_editor create /path/to/asdf`
    should return `str_replace_editor create`,
    `PYTHONPATH=/... python3.11 /testbed/test_file.py`
    should return `python`, etc.
    """
    if not action.strip():
        return ""
    action = strip_environment_variables(action)
    action = split_shell_commands(action)[-1]
    action = action.split('"')[0]
    action = action.split("'")[0]
    action = action.strip()
    if not action:
        return ""
    try:
        cmd_parts = shlex.split(action)
    except ValueError:
        cmd_parts = action.split()

    cmd_parts = cmd_parts[:2]
    cmd_parts = [p.strip() for p in cmd_parts if p.strip()]

    def is_option(s: str) -> bool:
        return s.startswith("-")

    def is_path(s: str) -> bool:
        return "/" in s or ".py" in s

    cmd_parts = [cmd_parts[0]] + [p for p in cmd_parts[1:] if not is_option(p) and not is_path(p)]

    if not cmd_parts:
        print(f"No cmd_parts for {action}")
        return ""

    if cmd_parts[0] != "str_replace_editor" and len(cmd_parts) > 1:
        cmd_parts = cmd_parts[:1]

    replace_dict = {
        "python3": "python",
        "python2": "python",
        "python3.11": "python",
    }

    cmd_parts[0] = replace_dict.get(cmd_parts[0], cmd_parts[0])

    return " ".join(cmd_parts)


def count_last_action_repetitions(actions: list[str]) -> int:
    """How often is the last action repeated consecutively?"""
    if not actions:
        return 0
    last_action = actions[-1]
    count = 0
    for action in reversed(actions):
        if get_base_command(action) == get_base_command(last_action):
            count += 1
        else:
            return count
    return count


class RepeatActionMitigator(AbstractAgentHook):
    def __init__(self, config: RepeatActionMitigatorConfig):
        self._config = config
        self._past_actions = []
        self._requery_count = 0  # How many times we've required
        self.logger = get_logger("RepeatActionMitigator")

    def on_run_start(self):
        self._past_actions = []
        self._requery_count = 0

    def get_repeat_action_count(self) -> int:
        """How often was the last base command repeated consecutively?"""
        return count_last_action_repetitions(self._past_actions)

    def get_injected_message(self) -> str:
        """Get the message that we append to the observation.
        If there's no repetitive command ongoing, return an empty string.
        """
        repeat_action_count = self.get_repeat_action_count()
        if not self._past_actions:
            return ""

        base_command = get_base_command(self._past_actions[-1])

        for warning_config in self._config.warning_messages:
            if warning_config.repetition_count > repeat_action_count:
                continue
            if not re.match(warning_config.base_action_regex, base_command):
                continue
            template = Template(warning_config.warning_message)
            return template.render(repetition_count=repeat_action_count, base_command=base_command)
        return ""

    def should_terminate(self) -> bool:
        """Should we terminate the agent due to repetitive actions?"""
        repeat_action_count = self.get_repeat_action_count()
        base_command = get_base_command(self._past_actions[-1])
        for termination_config in self._config.terminate:
            if termination_config.repetition_count > repeat_action_count:
                continue
            if not re.match(termination_config.base_action_regex, base_command):
                continue
            self.logger.warning(
                "Terminating due to repetitive actions: repetition_count: %d, base_command: %s",
                repeat_action_count,
                base_command,
            )
            return True
        return False

    def should_requery(self) -> tuple[bool, str]:
        """Should we requery the agent due to repetitive actions?

        Returns:
            Tuple of (should_requery, message_template)
        """
        if not self._past_actions:
            self._requery_count = 0
            return False, ""

        repeat_action_count = self.get_repeat_action_count()
        base_command = get_base_command(self._past_actions[-1])

        for requery_config in self._config.requery:
            if requery_config.repetition_count > repeat_action_count:
                continue
            if not re.match(requery_config.base_action_regex, base_command):
                continue

            if self._requery_count >= requery_config.max_requeries:
                self.logger.warning(
                    "Maximum requeries reached for base_command: %s (%d/%d)",
                    base_command,
                    self._requery_count,
                    requery_config.max_requeries,
                )
                self._requery_count = 0
                return False, ""

            template = Template(requery_config.requery_message_template)
            message = template.render(
                repetition_count=repeat_action_count, base_command=base_command, action=self._past_actions[-1]
            )
            self.logger.info(
                "Requerying due to repetitive actions: repetition_count: %d, base_command: %s, requery: %d/%d",
                repeat_action_count,
                base_command,
                self._requery_count,
                requery_config.max_requeries,
            )

            self._requery_count += 1
            return True, message

        self._requery_count = 0
        return False, ""

    def on_actions_generated(self, *, step: StepOutput):
        """Called after the actions have been generated.
        We append the action to the list of past actions and check if we should terminate.
        """
        should_requery, message = self.should_requery()
        if should_requery:
            raise BlockedActionError(message_template=message, exclude_from_format_fail_count=True)
        # Important: Only append the action after we've checked if we should requery
        self._past_actions.append(step.action)

    def on_action_executed(self, *, step: StepOutput):
        """Called after the step has been executed.
        We append the injected message to the observation.
        """
        injected_message = self.get_injected_message()
        if injected_message:
            step.observation += f"\n\n{injected_message}"
        if self.should_terminate():
            raise RepetitiveActionExit()
