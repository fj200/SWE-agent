from pydantic import BaseModel

from sweagent.agent.hooks.abstract import AbstractAgentHook
from sweagent.agent.hooks.config import InjectMessagesConfig, RepeatActionMitigatorConfig


# type: ignore
def get_hook_from_config(config: BaseModel) -> AbstractAgentHook:
    if isinstance(config, RepeatActionMitigatorConfig):
        from sweagent.agent.hooks.repeat_action_mitigator import RepeatActionMitigator

        return RepeatActionMitigator(config)
    elif isinstance(config, InjectMessagesConfig):
        from sweagent.agent.hooks.inject_messages import InjectMessages

        return InjectMessages(config)
    else:
        msg = f"Unsupported hook config: {config}"
        raise ValueError(msg)
