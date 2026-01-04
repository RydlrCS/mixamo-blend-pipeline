"""
Visualization and charting module for the Mixamo Blend Pipeline.

Provides comprehensive visualization functions for pipeline operations,
including performance metrics, agent statistics, learning curves, and
mission timeline animations.

Adapted from kijani-spiral (https://github.com/RydlrCS/kijani-spiral)

Author: Ted Iro
Organization: Rydlr Cloud Services Ltd
Date: January 4, 2026

Visualizations Provided:
    - Radar charts for agent/component capabilities
    - Reward and performance curves
    - Mission timeline animations (GIF)
    - Mission snapshots
    - Bar charts for comparative analysis
    - Statistical summary tables
    - Performance metrics dashboards
    - Learning curve analysis
"""

import logging
import io
import tempfile
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.figure import Figure

from src.utils.logging import get_logger

# Module-level logger
logger = get_logger(__name__)

# Check for optional dependencies
try:
    import imageio
    GIF_AVAILABLE = True
    logger.info("imageio available - GIF generation enabled")
except ImportError:
    GIF_AVAILABLE = False
    logger.warning("imageio not installed - GIF generation disabled")

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
    logger.info("pandas available - table generation enabled")
except ImportError:
    PANDAS_AVAILABLE = False
    logger.warning("pandas not installed - advanced table generation disabled")


# ============================================================================
# Data Classes for Visualization
# ============================================================================

@dataclass
class BlendMetrics:
    """Metrics for a blend operation."""
    operation_id: str
    start_time: float
    end_time: float
    frames_processed: int
    method: str  # linear, snn, spade
    status: str  # success, failure
    
    @property
    def duration(self) -> float:
        """Calculate operation duration."""
        return self.end_time - self.start_time


@dataclass
class AgentPerformance:
    """Performance metrics for an agent."""
    agent_id: str
    health: float
    morale: float
    energy: float
    total_reward: float
    objectives_completed: int
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'Agent': self.agent_id,
            'Health': f"{self.health:.1f}%",
            'Morale': f"{self.morale:.2f}",
            'Energy': f"{self.energy:.1f}%",
            'Reward': f"{self.total_reward:.2f}",
            'Objectives': self.objectives_completed,
        }


# ============================================================================
# Radar Charts
# ============================================================================

def create_agent_capabilities_radar(
    agent_stats: Dict[str, Dict[str, float]],
    title: str = "Agent Capabilities Radar",
    figsize: Tuple[int, int] = (10, 10)
) -> Figure:
    """
    Create a radar chart showing agent capabilities/statistics.
    
    Args:
        agent_stats: Dictionary mapping agent_id to attribute dict
                     Example: {"agent1": {"health": 85, "speed": 75, ...}, ...}
        title: Chart title
        figsize: Figure size tuple
        
    Returns:
        Matplotlib Figure object
        
    Example:
        >>> stats = {
        ...     "scout": {"health": 85, "speed": 95, "strength": 60},
        ...     "medic": {"health": 90, "speed": 70, "strength": 65}
        ... }
        >>> fig = create_agent_capabilities_radar(stats)
        >>> plt.show()
    """
    logger.info(f"Creating agent capabilities radar for {len(agent_stats)} agents")
    
    if not agent_stats:
        logger.warning("No agent stats provided")
        return None
    
    # Get attribute labels from first agent
    labels = list(next(iter(agent_stats.values())).keys())
    num_vars = len(labels)
    
    if num_vars < 2:
        logger.warning("Need at least 2 attributes for radar chart")
        return None
    
    # Compute angle for each axis
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    angles += angles[:1]  # Complete the circle
    
    # Create figure with polar projection
    fig, ax = plt.subplots(figsize=figsize, subplot_kw=dict(polar=True))
    
    # Color palette
    colors = plt.cm.Set3(np.linspace(0, 1, len(agent_stats)))
    
    # Plot each agent
    for (agent_id, stats), color in zip(agent_stats.items(), colors):
        values = list(stats.values())
        values += values[:1]  # Complete the circle
        
        ax.plot(angles, values, 'o-', linewidth=2, label=agent_id, color=color)
        ax.fill(angles, values, alpha=0.15, color=color)
    
    # Customize chart
    ax.set_thetagrids(np.degrees(angles[:-1]), labels, fontsize=11)
    ax.set_ylim(0, max(max(v) for s in agent_stats.values() for v in s.values()) * 1.1)
    ax.set_title(title, y=1.08, fontsize=14, fontweight='bold')
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=10)
    ax.grid(True, alpha=0.3)
    
    fig.tight_layout()
    logger.debug("Agent capabilities radar created successfully")
    
    return fig


def create_performance_metrics_radar(
    agent_performance: List[AgentPerformance],
    title: str = "Agent Performance Radar",
    figsize: Tuple[int, int] = (10, 10)
) -> Figure:
    """
    Create a radar chart showing agent performance metrics.
    
    Args:
        agent_performance: List of AgentPerformance objects
        title: Chart title
        figsize: Figure size tuple
        
    Returns:
        Matplotlib Figure object
    """
    logger.info(f"Creating performance radar for {len(agent_performance)} agents")
    
    # Convert to stats dictionary
    agent_stats = {}
    for perf in agent_performance:
        agent_stats[perf.agent_id] = {
            "Health": perf.health,
            "Morale": perf.morale * 100,  # Scale morale to 0-100
            "Energy": perf.energy,
            "Reward": perf.total_reward,
        }
    
    return create_agent_capabilities_radar(agent_stats, title=title, figsize=figsize)


# ============================================================================
# Line Charts and Curves
# ============================================================================

def create_reward_curve(
    reward_history: Dict[str, List[float]],
    title: str = "Cumulative Reward Over Time",
    figsize: Tuple[int, int] = (12, 6),
    xlabel: str = "Timestep",
    ylabel: str = "Cumulative Reward"
) -> Figure:
    """
    Create a line plot showing cumulative rewards over time.
    
    Args:
        reward_history: Dictionary mapping agent_id to list of reward values
        title: Chart title
        figsize: Figure size tuple
        xlabel: X-axis label
        ylabel: Y-axis label
        
    Returns:
        Matplotlib Figure object
        
    Example:
        >>> history = {
        ...     "agent1": [1.0, 2.5, 4.2, 6.8, 10.1],
        ...     "agent2": [0.8, 2.1, 3.9, 6.2, 9.5]
        ... }
        >>> fig = create_reward_curve(history)
        >>> plt.show()
    """
    logger.info(f"Creating reward curve for {len(reward_history)} agents")
    
    fig, ax = plt.subplots(figsize=figsize)
    
    # Color palette
    colors = plt.cm.Set2(np.linspace(0, 1, len(reward_history)))
    
    # Plot each agent's reward history
    for (agent_id, rewards), color in zip(reward_history.items(), colors):
        ax.plot(
            rewards,
            label=agent_id,
            linewidth=2.5,
            marker='o',
            markersize=4,
            alpha=0.8,
            color=color
        )
    
    # Customize chart
    ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.legend(loc='best', fontsize=10)
    
    fig.tight_layout()
    logger.debug("Reward curve created successfully")
    
    return fig


def create_performance_metrics_chart(
    metrics_history: Dict[str, Dict[str, List[float]]],
    title: str = "Agent Performance Metrics Over Time",
    figsize: Tuple[int, int] = (14, 10)
) -> Figure:
    """
    Create a multi-panel chart showing health, morale, and energy over time.
    
    Args:
        metrics_history: Dictionary like:
                        {"agent1": {"health": [...], "morale": [...], "energy": [...]}, ...}
        title: Main chart title
        figsize: Figure size tuple
        
    Returns:
        Matplotlib Figure object
        
    Example:
        >>> metrics = {
        ...     "agent1": {
        ...         "health": [100, 95, 90, 85],
        ...         "morale": [0.9, 0.85, 0.8, 0.75],
        ...         "energy": [100, 80, 60, 40]
        ...     }
        ... }
        >>> fig = create_performance_metrics_chart(metrics)
    """
    logger.info(f"Creating performance metrics chart for {len(metrics_history)} agents")
    
    # Create subplots for each metric type
    fig, axes = plt.subplots(3, 1, figsize=figsize)
    fig.suptitle(title, fontsize=14, fontweight='bold', y=0.995)
    
    metric_types = ["health", "morale", "energy"]
    colors = plt.cm.Set2(np.linspace(0, 1, len(metrics_history)))
    
    for ax, metric in zip(axes, metric_types):
        # Plot each agent's metric
        for (agent_id, metrics), color in zip(metrics_history.items(), colors):
            if metric in metrics:
                values = metrics[metric]
                ax.plot(
                    values,
                    label=agent_id,
                    linewidth=2,
                    marker='o',
                    markersize=4,
                    alpha=0.8,
                    color=color
                )
        
        # Customize subplot
        ax.set_ylabel(metric.capitalize(), fontsize=11)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.legend(loc='best', fontsize=9)
        
        if metric == "energy":
            ax.set_xlabel("Timestep", fontsize=11)
    
    fig.tight_layout()
    logger.debug("Performance metrics chart created successfully")
    
    return fig


def create_learning_curve(
    training_history: Dict[str, List[float]],
    title: str = "Learning Curve - Q-Learning Training",
    figsize: Tuple[int, int] = (12, 6)
) -> Figure:
    """
    Create a learning curve showing training progress.
    
    Args:
        training_history: Dictionary mapping agent_id to list of episode rewards
        title: Chart title
        figsize: Figure size tuple
        
    Returns:
        Matplotlib Figure object
    """
    logger.info(f"Creating learning curve for {len(training_history)} agents")
    
    fig, ax = plt.subplots(figsize=figsize)
    
    colors = plt.cm.Set2(np.linspace(0, 1, len(training_history)))
    
    for (agent_id, history), color in zip(training_history.items(), colors):
        # Calculate moving average
        window_size = max(1, len(history) // 20)
        moving_avg = np.convolve(history, np.ones(window_size)/window_size, mode='valid')
        
        ax.plot(history, alpha=0.2, color=color, linewidth=0.5)
        ax.plot(moving_avg, label=f"{agent_id} (moving avg)", linewidth=2.5, color=color)
    
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.set_xlabel("Episode", fontsize=12)
    ax.set_ylabel("Episode Reward", fontsize=12)
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best', fontsize=10)
    
    fig.tight_layout()
    logger.debug("Learning curve created successfully")
    
    return fig


# ============================================================================
# Bar Charts and Comparative Visualizations
# ============================================================================

def create_final_rewards_bar_chart(
    agent_rewards: Dict[str, float],
    title: str = "Final Agent Rewards",
    figsize: Tuple[int, int] = (10, 6)
) -> Figure:
    """
    Create a bar chart comparing final rewards across agents.
    
    Args:
        agent_rewards: Dictionary mapping agent_id to final reward
        title: Chart title
        figsize: Figure size tuple
        
    Returns:
        Matplotlib Figure object
    """
    logger.info(f"Creating final rewards bar chart for {len(agent_rewards)} agents")
    
    fig, ax = plt.subplots(figsize=figsize)
    
    agents = list(agent_rewards.keys())
    rewards = list(agent_rewards.values())
    
    # Create bars with color gradient
    colors = plt.cm.RdYlGn(np.linspace(0.3, 0.9, len(agents)))
    bars = ax.bar(agents, rewards, color=colors, edgecolor='black', linewidth=1.5)
    
    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width()/2.,
            height,
            f'{height:.2f}',
            ha='center',
            va='bottom',
            fontsize=10,
            fontweight='bold'
        )
    
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.set_xlabel("Agent", fontsize=12)
    ax.set_ylabel("Final Reward", fontsize=12)
    ax.grid(axis='y', alpha=0.3)
    
    fig.tight_layout()
    logger.debug("Final rewards bar chart created successfully")
    
    return fig


def create_objectives_completion_chart(
    agent_objectives: Dict[str, int],
    total_objectives: int = None,
    title: str = "Objectives Completed by Agent",
    figsize: Tuple[int, int] = (10, 6)
) -> Figure:
    """
    Create a bar chart showing objectives completed by each agent.
    
    Args:
        agent_objectives: Dictionary mapping agent_id to objectives_completed
        total_objectives: Total objectives available (for percentage display)
        title: Chart title
        figsize: Figure size tuple
        
    Returns:
        Matplotlib Figure object
    """
    logger.info(f"Creating objectives chart for {len(agent_objectives)} agents")
    
    fig, ax = plt.subplots(figsize=figsize)
    
    agents = list(agent_objectives.keys())
    objectives = list(agent_objectives.values())
    
    colors = plt.cm.Blues(np.linspace(0.4, 0.9, len(agents)))
    bars = ax.bar(agents, objectives, color=colors, edgecolor='black', linewidth=1.5)
    
    # Add value labels
    for bar in bars:
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width()/2.,
            height,
            f'{int(height)}',
            ha='center',
            va='bottom',
            fontsize=10,
            fontweight='bold'
        )
    
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.set_xlabel("Agent", fontsize=12)
    ax.set_ylabel("Objectives Completed", fontsize=12)
    ax.grid(axis='y', alpha=0.3)
    
    if total_objectives:
        ax.set_ylim(0, total_objectives * 1.1)
    
    fig.tight_layout()
    logger.debug("Objectives completion chart created successfully")
    
    return fig


# ============================================================================
# Mission Timeline Visualizations
# ============================================================================

def create_mission_timeline_gif(
    trajectories: Dict[str, List[Tuple[float, float]]],
    title_prefix: str = "Mission Timeline",
    duration: float = 0.15,
    figsize: Tuple[int, int] = (8, 8),
    dpi: int = 100
) -> Optional[str]:
    """
    Create an animated GIF showing agent movement over time.
    
    Args:
        trajectories: Dictionary mapping agent_id to list of (x, y) positions
        title_prefix: Prefix for frame titles
        duration: Frame duration in seconds
        figsize: Figure size tuple
        dpi: DPI for rendered frames
        
    Returns:
        Path to generated GIF file, or None if imageio not available
        
    Note:
        Requires imageio to be installed
    """
    if not GIF_AVAILABLE:
        logger.warning("Cannot create GIF - imageio not installed")
        return None
    
    logger.info(f"Creating mission timeline GIF with {len(trajectories)} agents")
    
    # Determine number of frames
    num_frames = max(len(traj) for traj in trajectories.values())
    if num_frames < 2:
        logger.warning("Need at least 2 timesteps for animation")
        return None
    
    logger.debug(f"Generating {num_frames} frames")
    frames = []
    
    # Determine axis limits
    all_x = [pos[0] for traj in trajectories.values() for pos in traj]
    all_y = [pos[1] for traj in trajectories.values() for pos in traj]
    x_min, x_max = min(all_x), max(all_x)
    y_min, y_max = min(all_y), max(all_y)
    x_margin = (x_max - x_min) * 0.1
    y_margin = (y_max - y_min) * 0.1
    
    # Generate each frame
    for t in range(num_frames):
        fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
        ax.set_xlim(x_min - x_margin, x_max + x_margin)
        ax.set_ylim(y_min - y_margin, y_max + y_margin)
        ax.set_xlabel("X Position", fontsize=10)
        ax.set_ylabel("Y Position", fontsize=10)
        ax.set_title(f"{title_prefix} (t={t})", fontweight='bold', fontsize=12)
        ax.grid(True, alpha=0.3)
        
        colors = plt.cm.Set1(np.linspace(0, 1, len(trajectories)))
        
        # Plot each agent's position and trail
        for (agent_id, trajectory), color in zip(trajectories.items(), colors):
            if t < len(trajectory):
                # Plot trail up to current time
                trail_x = [pos[0] for pos in trajectory[:t+1]]
                trail_y = [pos[1] for pos in trajectory[:t+1]]
                ax.plot(trail_x, trail_y, alpha=0.5, linewidth=1.5, color=color)
                
                # Plot current position
                x, y = trajectory[t]
                ax.scatter([x], [y], s=150, alpha=0.9, edgecolors='black',
                          linewidths=2, color=color)
                ax.text(x, y + (y_margin * 0.3), f"{agent_id}", fontsize=9,
                       ha='center', fontweight='bold')
        
        fig.tight_layout()
        
        # Render to buffer
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=dpi)
        plt.close(fig)
        buf.seek(0)
        
        # Read as image
        frames.append(imageio.v2.imread(buf))
        buf.close()
        
        if (t + 1) % max(1, num_frames // 5) == 0:
            logger.debug(f"Generated frame {t + 1}/{num_frames}")
    
    # Save as GIF
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".gif")
    output_path = temp_file.name
    temp_file.close()
    
    imageio.mimsave(output_path, frames, duration=duration)
    logger.info(f"Mission timeline GIF saved to: {output_path}")
    
    return output_path


def create_mission_snapshot(
    trajectories: Dict[str, List[Tuple[float, float]]],
    current_timestep: int,
    title: str = "Mission Snapshot",
    figsize: Tuple[int, int] = (10, 10)
) -> Figure:
    """
    Create a static snapshot of agent positions at a specific timestep.
    
    Args:
        trajectories: Dictionary mapping agent_id to list of (x, y) positions
        current_timestep: Timestep to visualize
        title: Chart title
        figsize: Figure size tuple
        
    Returns:
        Matplotlib Figure object
    """
    logger.info(f"Creating mission snapshot at timestep {current_timestep}")
    
    fig, ax = plt.subplots(figsize=figsize)
    
    # Determine axis limits
    all_x = [pos[0] for traj in trajectories.values() for pos in traj]
    all_y = [pos[1] for traj in trajectories.values() for pos in traj]
    x_min, x_max = min(all_x), max(all_x)
    y_min, y_max = min(all_y), max(all_y)
    x_margin = (x_max - x_min) * 0.1
    y_margin = (y_max - y_min) * 0.1
    
    ax.set_xlim(x_min - x_margin, x_max + x_margin)
    ax.set_ylim(y_min - y_margin, y_max + y_margin)
    ax.set_xlabel("X Position", fontsize=12)
    ax.set_ylabel("Y Position", fontsize=12)
    ax.set_title(f"{title} (t={current_timestep})", fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    
    colors = plt.cm.Set1(np.linspace(0, 1, len(trajectories)))
    
    # Plot each agent
    for (agent_id, trajectory), color in zip(trajectories.items(), colors):
        if current_timestep < len(trajectory):
            # Plot full trail
            trail_x = [pos[0] for pos in trajectory[:current_timestep+1]]
            trail_y = [pos[1] for pos in trajectory[:current_timestep+1]]
            ax.plot(trail_x, trail_y, alpha=0.6, linewidth=2, label=agent_id, color=color)
            
            # Plot current position
            x, y = trajectory[current_timestep]
            ax.scatter([x], [y], s=200, alpha=0.9, edgecolors='black', linewidths=2.5,
                      color=color)
            ax.text(x, y + (y_margin * 0.3), agent_id, fontsize=11, ha='center',
                   fontweight='bold')
    
    ax.legend(loc='best', fontsize=10)
    fig.tight_layout()
    
    logger.debug("Mission snapshot created successfully")
    return fig


# ============================================================================
# Summary Tables
# ============================================================================

def create_performance_summary_table(
    agent_performances: List[AgentPerformance],
    title: str = "Agent Performance Summary"
) -> Optional[str]:
    """
    Create a summary table of agent performance metrics.
    
    Args:
        agent_performances: List of AgentPerformance objects
        title: Table title
        
    Returns:
        Formatted table string (or DataFrame if pandas available)
    """
    logger.info(f"Creating performance summary table for {len(agent_performances)} agents")
    
    if PANDAS_AVAILABLE:
        # Use pandas for better formatting
        data = [perf.to_dict() for perf in agent_performances]
        df = pd.DataFrame(data)
        
        logger.debug("Performance summary table created with pandas")
        return df
    else:
        # Manual table creation
        table_str = f"\n{'='*80}\n{title}\n{'='*80}\n"
        table_str += f"{'Agent':<15} {'Health':<12} {'Morale':<12} {'Energy':<12} {'Reward':<12} {'Objectives':<10}\n"
        table_str += "-" * 80 + "\n"
        
        for perf in agent_performances:
            table_str += f"{perf.agent_id:<15} {perf.health:<11.1f}% {perf.morale:<11.2f} {perf.energy:<11.1f}% {perf.total_reward:<11.2f} {perf.objectives_completed:<9}\n"
        
        table_str += "=" * 80 + "\n"
        logger.debug("Performance summary table created manually")
        return table_str


def create_statistics_summary(
    agent_performances: List[AgentPerformance],
    title: str = "Statistics Summary"
) -> str:
    """
    Create a statistical summary of all agents.
    
    Args:
        agent_performances: List of AgentPerformance objects
        title: Summary title
        
    Returns:
        Formatted summary string
    """
    logger.info(f"Creating statistics summary for {len(agent_performances)} agents")
    
    if not agent_performances:
        logger.warning("No agent performances provided")
        return ""
    
    health_values = [p.health for p in agent_performances]
    morale_values = [p.morale for p in agent_performances]
    energy_values = [p.energy for p in agent_performances]
    reward_values = [p.total_reward for p in agent_performances]
    
    summary = f"\n{'='*60}\n{title}\n{'='*60}\n\n"
    
    summary += "HEALTH Statistics:\n"
    summary += f"  Mean:   {np.mean(health_values):.2f}%\n"
    summary += f"  Median: {np.median(health_values):.2f}%\n"
    summary += f"  Std:    {np.std(health_values):.2f}%\n"
    summary += f"  Min:    {np.min(health_values):.2f}%\n"
    summary += f"  Max:    {np.max(health_values):.2f}%\n\n"
    
    summary += "MORALE Statistics:\n"
    summary += f"  Mean:   {np.mean(morale_values):.2f}\n"
    summary += f"  Median: {np.median(morale_values):.2f}\n"
    summary += f"  Std:    {np.std(morale_values):.2f}\n"
    summary += f"  Min:    {np.min(morale_values):.2f}\n"
    summary += f"  Max:    {np.max(morale_values):.2f}\n\n"
    
    summary += "ENERGY Statistics:\n"
    summary += f"  Mean:   {np.mean(energy_values):.2f}%\n"
    summary += f"  Median: {np.median(energy_values):.2f}%\n"
    summary += f"  Std:    {np.std(energy_values):.2f}%\n"
    summary += f"  Min:    {np.min(energy_values):.2f}%\n"
    summary += f"  Max:    {np.max(energy_values):.2f}%\n\n"
    
    summary += "REWARD Statistics:\n"
    summary += f"  Mean:   {np.mean(reward_values):.2f}\n"
    summary += f"  Median: {np.median(reward_values):.2f}\n"
    summary += f"  Std:    {np.std(reward_values):.2f}\n"
    summary += f"  Min:    {np.min(reward_values):.2f}\n"
    summary += f"  Max:    {np.max(reward_values):.2f}\n"
    summary += f"  Total:  {np.sum(reward_values):.2f}\n\n"
    
    summary += "=" * 60 + "\n"
    
    logger.debug("Statistics summary created successfully")
    return summary


# ============================================================================
# Utility Functions
# ============================================================================

def close_all_figures() -> None:
    """
    Close all matplotlib figures to free memory.
    
    Useful for batch processing or notebook environments.
    """
    plt.close('all')
    logger.debug("All matplotlib figures closed")


def save_figure(fig: Figure, filepath: str, dpi: int = 300, **kwargs) -> None:
    """
    Save a matplotlib figure to file.
    
    Args:
        fig: Matplotlib Figure object
        filepath: Output file path
        dpi: Resolution (dots per inch)
        **kwargs: Additional arguments for savefig
    """
    logger.info(f"Saving figure to {filepath}")
    
    try:
        fig.savefig(filepath, dpi=dpi, bbox_inches='tight', **kwargs)
        logger.debug(f"Figure saved successfully: {filepath}")
    except Exception as e:
        logger.error(f"Failed to save figure: {e}", exc_info=True)
        raise
