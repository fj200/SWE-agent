from pydantic import BaseModel

from sweagent.agent.hooks.abstract import AbstractAgentHook
from sweagent.agent.hooks.config import RepeatActionMitigatorConfig


# type: ignore
def get_hook_from_config(config: BaseModel) -> AbstractAgentHook:
    if isinstance(config, RepeatActionMitigatorConfig):
        from sweagent.agent.hooks.repeat_action_mitigator import RepeatActionMitigator

        return RepeatActionMitigator(config)
    else:
        msg = f"Unsupported hook config: {config}"
        raise ValueError(msg)
