"""NPC Engine for kijani-spiral integration.

Orchestrates multi-agent missions with blended animations.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class MissionResult:
    """Results from NPC mission execution."""

    success: bool
    mission_id: str
    total_reward: float = 0.0
    objectives_completed: int = 0
    agents_data: Dict[str, Any] = field(default_factory=dict)
    animation_sequences: Dict[str, List[str]] = field(default_factory=dict)
    error_message: Optional[str] = None
    execution_time_seconds: float = 0.0


class NPCEngine:
    """Integration layer for kijani-spiral multi-agent missions.

    Orchestrates multi-agent scenarios, manages animation blending for agent
    movements, and executes ethical decision-making simulations.
    """

    def __init__(self) -> None:
        """Initialize NPC Engine."""
        self.mission_id: Optional[str] = None
        self.agents: Dict[str, Any] = {}
        self.scenario: Optional[Dict[str, Any]] = None
        self.blended_animations: Dict[str, str] = {}
        logger.info("NPC Engine initialized")

    def register_agent(
        self,
        agent_id: str,
        role: str,
        animation_path: Optional[str] = None,
    ) -> bool:
        """Register an agent for the mission.

        Args:
            agent_id: Unique identifier for the agent
            role: Agent role (scout, medic, assault, etc.)
            animation_path: Path to blended animation for this agent

        Returns:
            True if registration successful, False otherwise
        """
        try:
            if agent_id in self.agents:
                logger.warning(f"Agent {agent_id} already registered")
                return False

            self.agents[agent_id] = {
                "role": role,
                "animation_path": animation_path,
                "status": "ready",
            }

            logger.info(f"Agent {agent_id} registered with role {role}")
            return True

        except Exception as e:  # pragma: no cover - defensive logging
            logger.error(f"Failed to register agent {agent_id}: {e}")
            return False

    def inject_animation(
        self,
        agent_id: str,
        animation_path: str,
    ) -> bool:
        """Inject a blended animation into an agent's behavior sequence.

        Args:
            agent_id: ID of agent to inject animation into
            animation_path: Path to blended animation file

        Returns:
            True if injection successful
        """
        try:
            if agent_id not in self.agents:
                logger.error(f"Agent {agent_id} not found")
                return False

            self.agents[agent_id]["animation_path"] = animation_path
            self.blended_animations[agent_id] = animation_path

            logger.info(f"Animation injected for agent {agent_id}: {animation_path}")
            return True

        except Exception as e:  # pragma: no cover - defensive logging
            logger.error(f"Failed to inject animation for {agent_id}: {e}")
            return False

    def load_mission_scenario(
        self,
        scenario_config: Dict[str, Any],
    ) -> bool:
        """Load a mission scenario configuration.

        Args:
            scenario_config: Mission scenario dictionary with objectives,
                           obstacles, constraints, etc.

        Returns:
            True if scenario loaded successfully
        """
        try:
            if not scenario_config:
                logger.error("Empty scenario configuration provided")
                return False

            self.scenario = scenario_config
            logger.info(
                f"Mission scenario loaded: {scenario_config.get('name', 'unnamed')}"
            )
            return True

        except Exception as e:  # pragma: no cover - defensive logging
            logger.error(f"Failed to load scenario: {e}")
            return False

    def execute_mission(
        self,
        mission_id: str,
        timesteps: int = 60,
        ethics_enabled: bool = True,
    ) -> MissionResult:
        """Execute a multi-agent mission.

        Args:
            mission_id: Unique identifier for this mission execution
            timesteps: Number of simulation timesteps to run
            ethics_enabled: Enable ethics-aware reward shaping

        Returns:
            MissionResult with execution details and outcomes
        """
        import time

        start_time = time.time()
        self.mission_id = mission_id

        try:
            # Validate mission prerequisites
            if not self.agents:
                error_msg = "No agents registered for mission"
                logger.error(error_msg)
                return MissionResult(
                    success=False,
                    mission_id=mission_id,
                    error_message=error_msg,
                    execution_time_seconds=time.time() - start_time,
                )

            if not self.scenario:
                error_msg = "No scenario loaded for mission"
                logger.error(error_msg)
                return MissionResult(
                    success=False,
                    mission_id=mission_id,
                    error_message=error_msg,
                    execution_time_seconds=time.time() - start_time,
                )

            logger.info(
                f"Executing mission {mission_id} with {len(self.agents)} agents"
            )
            logger.info(
                f"Timesteps: {timesteps}, Ethics Enabled: {ethics_enabled}"
            )

            # Placeholder: SOFTKILL-9000 integration pending
            # When integrated, this will call the actual simulator
            total_reward = 0.0
            objectives_completed = 0
            agent_data: Dict[str, Any] = {}

            # Build agent data from registered agents
            for agent_id, agent_info in self.agents.items():
                agent_data[agent_id] = {
                    "role": agent_info["role"],
                    "animation": agent_info["animation_path"],
                    "reward": 0.0,
                    "actions": [],
                }
                logger.info(
                    f"Agent {agent_id} ({agent_info['role']}) included in mission"
                )

            # Placeholder simulation results
            objectives_completed = len(self.scenario.get("objectives", []))
            total_reward = float(objectives_completed * 5.0)

            execution_time = time.time() - start_time

            logger.info(f"Mission {mission_id} completed successfully")
            logger.info(f"Total Reward: {total_reward:.2f}")
            logger.info(f"Objectives Completed: {objectives_completed}")

            return MissionResult(
                success=True,
                mission_id=mission_id,
                total_reward=total_reward,
                objectives_completed=objectives_completed,
                agents_data=agent_data,
                animation_sequences={
                    aid: [agent_info.get("animation_path", "")]
                    for aid, agent_info in self.agents.items()
                },
                execution_time_seconds=execution_time,
            )

        except Exception as e:  # pragma: no cover - defensive logging
            logger.error(f"Mission execution failed: {e}", exc_info=True)
            return MissionResult(
                success=False,
                mission_id=mission_id,
                error_message=str(e),
                execution_time_seconds=time.time() - start_time,
            )

    def get_mission_stats(self) -> Dict[str, Any]:
        """Get statistics about the current mission.

        Returns:
            Dictionary with mission statistics
        """
        return {
            "mission_id": self.mission_id,
            "num_agents": len(self.agents),
            "agents": list(self.agents.keys()),
            "blended_animations": len(self.blended_animations),
            "scenario_loaded": self.scenario is not None,
        }

    def reset(self) -> None:
        """Reset engine to initial state."""
        self.mission_id = None
        self.agents = {}
        self.scenario = None
        self.blended_animations = {}
        logger.info("NPC Engine reset")
