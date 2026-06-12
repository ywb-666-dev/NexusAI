"""NexusAI 5-Agent Architecture

LangGraph 状态机: Scout → Parser → Connector → Actor → Curator
"""

from .state import (
    NexusState,
    ScoutResult,
    ParserResult,
    ConnectorResult,
    ActorResult,
    CuratorResult,
)
from .supervisor import NexusSupervisor
from .scout_agent import run_scout_node, _update_task_status, get_task_status, AGENT_NODES
from .parser_agent import run_parser
from .connector_agent import run_connector
from .actor_agent import run_actor
from .curator_agent import run_curator

__all__ = [
    "NexusState",
    "ScoutResult",
    "ParserResult",
    "ConnectorResult",
    "ActorResult",
    "CuratorResult",
    "NexusSupervisor",
    "run_scout_node",
    "run_parser",
    "run_connector",
    "run_actor",
    "run_curator",
    "_update_task_status",
    "get_task_status",
    "AGENT_NODES",
]
