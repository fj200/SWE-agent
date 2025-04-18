from typing import Annotated, Literal

from pydantic import BaseModel, Field


class RAMWarningMessageConfig(BaseModel):
    base_action_regex: str
    """Regex for the base action."""

    repetition_count: int
    """How often the action was repeated."""

    warning_message: str
    """The warning message to display.
    You can use jinja with the following variables:
    - repetition_count: How often the action was repeated
    - base_command: The base command of the action
    """


class RAMTerminationConfig(BaseModel):
    base_action_regex: str
    """Regex for the base action."""

    repetition_count: int
    """How often the action was repeated."""


class RepeatActionMitigatorConfig(BaseModel):
    warning_messages: list[RAMWarningMessageConfig] = []
    """List of warning messages to display.
    If multiple things apply, the first one in the list is used.
    """

    terminate: list[RAMTerminationConfig] = []
    """List of (base_command regex, repetition_count)
    If the repetition count is reached, the agent will be terminated.
    """

    type: Literal["repeat_action_mitigator"] = "repeat_action_mitigator"
    """Do not change this."""


AgentHookConfig = Annotated[RepeatActionMitigatorConfig, Field(discriminator="type")]
