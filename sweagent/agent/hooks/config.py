from typing import Annotated, Literal

from pydantic import BaseModel, Field


class RepeatActionMitigatorConfig(BaseModel):
    warning_messages: dict[tuple[str, int], str] = {}
    """Mapping of (base_command regex, repetition_count) -> warning message.
    If multiple things apply, the first one in the dict is used.
    You can use jinja with the following variables:
    - repetition_count: How often the action was repeated
    - base_command: The base command of the action
    """

    terminate: list[tuple[str, int]] = []
    """List of (base_command regex, repetition_count)
    If the repetition count is reached, the agent will be terminated.
    """

    type: Literal["repeat_action_mitigator"] = "repeat_action_mitigator"
    """Do not change this."""


AgentHookConfig = Annotated[RepeatActionMitigatorConfig, Field(discriminator="type")]
