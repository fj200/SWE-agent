from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


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

    model_config = ConfigDict(extra="forbid")


class RAMTerminationConfig(BaseModel):
    base_action_regex: str
    """Regex for the base action."""

    repetition_count: int
    """How often the action was repeated."""

    model_config = ConfigDict(extra="forbid")


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

    add_error_template_as_assistant_message: bool = False
    """If true, the error template will be added as an assistant message to the requery history."""

    model_config = ConfigDict(extra="forbid")


class RAMRollbackHistoryConfig(BaseModel):
    base_action_regex: str
    """Regex for the base action."""

    repetition_count: int
    """How often the action was repeated."""

    rollback_step_offset: int
    """How many additional steps to roll back."""

    model_config = ConfigDict(extra="forbid")


class InjectMessagesConfig(BaseModel):
    messages: list[dict[str, str]] = []
    """List of messages to inject in the format [{"role": "user", "content": "message"}, ...]"""

    inject_after_step: int
    """Step number after which to inject the messages."""

    type: Literal["inject_messages"] = "inject_messages"
    """Do not change this."""

    model_config = ConfigDict(extra="forbid")


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

    rollback_history: list[RAMRollbackHistoryConfig] = []
    """List of rollback history configurations.
    """
    max_rollbacks: int = 0
    """Maximum number of rollbacks. Set to 0 for unlimited rollbacks."""

    type: Literal["repeat_action_mitigator"] = "repeat_action_mitigator"
    """Do not change this."""

    model_config = ConfigDict(extra="forbid")


AgentHookConfig = Annotated[RepeatActionMitigatorConfig | InjectMessagesConfig, Field(discriminator="type")]
