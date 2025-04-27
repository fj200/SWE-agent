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


class RAMRequeryConfig(BaseModel):
    base_action_regex: str
    """Regex for the base action."""

    repetition_count: int
    """Trigger when action was repeated this many times"""

    max_requeries: int
    """Maximum number of requeries."""

    requery_message_template: str
    """Shown to the model when requerying.
    Available fields: action, repetition_count, base_command
    """

    requery_temperature: float | None = None
    """Temperature to use for requery
    """


class RepeatActionMitigatorConfig(BaseModel):
    warning_messages: list[RAMWarningMessageConfig] = []
    """List of warning messages to display.
    If multiple things apply, the first one in the list is used.
    """

    terminate: list[RAMTerminationConfig] = []
    """List of (base_command regex, repetition_count)
    If the repetition count is reached, the agent will be terminated.
    """

    requery: list[RAMRequeryConfig] = []
    """List of requery configurations.
    """

    type: Literal["repeat_action_mitigator"] = "repeat_action_mitigator"
    """Do not change this."""


AgentHookConfig = Annotated[RepeatActionMitigatorConfig, Field(discriminator="type")]
