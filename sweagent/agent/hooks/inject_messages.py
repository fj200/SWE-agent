"""
Hook for injecting messages at specific steps in the agent's history.
"""

from sweagent.agent.hooks.abstract import AbstractAgentHook
from sweagent.agent.hooks.config import InjectMessagesConfig
from sweagent.types import AgentInfo, StepOutput
from sweagent.utils.log import get_logger


class InjectMessages(AbstractAgentHook):
    """Hook for injecting messages at specific steps in the agent's history."""

    def __init__(self, config: InjectMessagesConfig):
        """Initialize the hook.

        Args:
            config: The configuration for the hook.
        """
        self._config = config
        self._step_count = 0
        self._agent = None
        self.logger = get_logger("InjectMessages", emoji="💉")

    def on_init(self, *, agent):
        """Store reference to the agent.

        Args:
            agent: The agent this hook is attached to.
        """
        self._agent = agent

    def on_run_start(self):
        """Reset the step counter and injected flag when a new run starts."""
        self._step_count = 0

    def on_step_done(self, *, step: StepOutput, info: AgentInfo):
        """Increment the step counter and inject messages if needed.

        Args:
            step: The completed step.
            info: The agent info.
        """
        self._step_count += 1

        if self._step_count == self._config.inject_after_step:
            self.logger.info(f"Injecting messages {self._config.messages}")
            self._inject_messages()

    def _inject_messages(self):
        """Inject the configured messages into the agent's history."""
        assert self._agent is not None

        for message in self._config.messages:
            # Validate message has required fields
            if "role" not in message or "content" not in message:
                msg = f"Message {message} has missing required fields"
                raise ValueError(msg)

            self._agent._append_history(
                {
                    "role": message["role"],
                    "content": message["content"],
                    "agent": self._agent.name,
                    "message_type": "injected",
                }
            )
