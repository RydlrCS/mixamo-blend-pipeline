"""
Dashboard module for comprehensive pipeline visualization.

Provides high-level functions for creating multi-panel dashboards and
complete visualization suites for pipeline operations and metrics analysis.

Author: Ted Iro
Organization: Rydlr Cloud Services Ltd
Date: January 4, 2026
"""

import logging
from typing import Dict, List, Optional, Tuple
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

from src.utils.logging import get_logger
from src.utils.visualizations import (
    create_agent_capabilities_radar,
    create_reward_curve,
    create_performance_metrics_chart,
    create_final_rewards_bar_chart,
    create_learning_curve,
    AgentPerformance,
    create_performance_summary_table,
    create_statistics_summary,
)

# Module-level logger
logger = get_logger(__name__)


# ============================================================================
# Dashboard Functions
# ============================================================================

def create_mission_performance_dashboard(
    reward_history: Dict[str, List[float]],
    agent_stats: Dict[str, Dict[str, float]],
    final_rewards: Dict[str, float],
    figsize: Tuple[int, int] = (16, 12),
    title: str = "Mission Performance Dashboard"
) -> Figure:
    """
    Create a comprehensive mission performance dashboard.
    
    Includes:
    - Cumulative reward curves
    - Agent capabilities radar
    - Final rewards comparison
    
    Args:
        reward_history: Dict mapping agent_id to reward list
        agent_stats: Dict mapping agent_id to stats dict
        final_rewards: Dict mapping agent_id to final reward
        figsize: Figure size tuple
        title: Dashboard title
        
    Returns:
        Matplotlib Figure object
        
    Example:
        >>> dashboard = create_mission_performance_dashboard(
        ...     reward_history={"agent1": [1, 2, 3], "agent2": [1.5, 2.8, 4.2]},
        ...     agent_stats={"agent1": {"health": 85, "speed": 90}, ...},
        ...     final_rewards={"agent1": 3.0, "agent2": 4.2}
        ... )
        >>> plt.show()
    """
    logger.info("Creating mission performance dashboard")
    
    fig = plt.figure(figsize=figsize)
    fig.suptitle(title, fontsize=16, fontweight='bold', y=0.995)
    
    # Create grid spec for subplots
    gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)
    
    # 1. Reward curves (top left)
    ax1 = fig.add_subplot(gs[0, 0])
    colors = plt.cm.Set2(range(len(reward_history)))
    for (agent_id, rewards), color in zip(reward_history.items(), colors):
        ax1.plot(rewards, label=agent_id, linewidth=2, marker='o', markersize=4, color=color)
    ax1.set_title("Cumulative Reward Progression", fontsize=12, fontweight='bold')
    ax1.set_xlabel("Timestep")
    ax1.set_ylabel("Cumulative Reward")
    ax1.grid(True, alpha=0.3)
    ax1.legend(fontsize=9)
    
    # 2. Agent capabilities radar (top right)
    ax2 = fig.add_subplot(gs[0, 1], projection='polar')
    labels = list(next(iter(agent_stats.values())).keys())
    num_vars = len(labels)
    angles = [n / float(num_vars) * 2 * 3.14159 for n in range(num_vars)]
    angles += angles[:1]
    
    for agent_id, stats in agent_stats.items():
        values = list(stats.values()) + [list(stats.values())[0]]
        ax2.plot(angles, values, 'o-', linewidth=2, label=agent_id)
        ax2.fill(angles, values, alpha=0.15)
    
    ax2.set_xticks([angle for angle in angles[:-1]])
    ax2.set_xticklabels(labels, fontsize=9)
    ax2.set_ylim(0, max(max(v) for s in agent_stats.values() for v in s.values()) * 1.1)
    ax2.set_title("Agent Capabilities", fontsize=12, fontweight='bold', pad=20)
    ax2.legend(loc='upper right', bbox_to_anchor=(1.2, 1.0), fontsize=9)
    ax2.grid(True)
    
    # 3. Final rewards (bottom left)
    ax3 = fig.add_subplot(gs[1, 0])
    agents = list(final_rewards.keys())
    rewards = list(final_rewards.values())
    colors_bar = plt.cm.RdYlGn([(r - min(rewards)) / (max(rewards) - min(rewards)) for r in rewards])
    bars = ax3.bar(agents, rewards, color=colors_bar, edgecolor='black', linewidth=1.5)
    for bar in bars:
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height, f'{height:.2f}',
                ha='center', va='bottom', fontsize=10, fontweight='bold')
    ax3.set_title("Final Agent Rewards", fontsize=12, fontweight='bold')
    ax3.set_ylabel("Final Reward")
    ax3.grid(axis='y', alpha=0.3)
    
    # 4. Statistics (bottom right - text)
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.axis('off')
    
    stats_text = "Summary Statistics\n" + "="*30 + "\n\n"
    reward_values = list(final_rewards.values())
    stats_text += f"Total Reward: {sum(reward_values):.2f}\n"
    stats_text += f"Avg Reward: {sum(reward_values)/len(reward_values):.2f}\n"
    stats_text += f"Max Reward: {max(reward_values):.2f}\n"
    stats_text += f"Min Reward: {min(reward_values):.2f}\n"
    stats_text += f"\nAgents: {len(final_rewards)}\n"
    
    ax4.text(0.1, 0.9, stats_text, transform=ax4.transAxes, fontsize=11,
            verticalalignment='top', family='monospace',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    logger.debug("Mission performance dashboard created successfully")
    return fig


def create_agent_performance_dashboard(
    agent_performances: List[AgentPerformance],
    metrics_history: Dict[str, Dict[str, List[float]]],
    figsize: Tuple[int, int] = (16, 10),
    title: str = "Agent Performance Dashboard"
) -> Figure:
    """
    Create a comprehensive agent performance dashboard.
    
    Includes:
    - Performance metrics over time (health, morale, energy)
    - Agent capabilities radar
    - Summary statistics
    
    Args:
        agent_performances: List of AgentPerformance objects
        metrics_history: Dict like {"agent1": {"health": [...], ...}, ...}
        figsize: Figure size tuple
        title: Dashboard title
        
    Returns:
        Matplotlib Figure object
    """
    logger.info("Creating agent performance dashboard")
    
    fig = plt.figure(figsize=figsize)
    fig.suptitle(title, fontsize=16, fontweight='bold', y=0.98)
    
    gs = fig.add_gridspec(2, 3, hspace=0.35, wspace=0.3)
    
    colors = plt.cm.Set2(range(len(agent_performances)))
    metric_colors = {'health': '#FF6B6B', 'morale': '#4ECDC4', 'energy': '#45B7D1'}
    
    # Performance curves (top row)
    metric_types = ['health', 'morale', 'energy']
    for idx, metric in enumerate(metric_types):
        ax = fig.add_subplot(gs[0, idx])
        for agent_id, metrics in metrics_history.items():
            if metric in metrics:
                ax.plot(metrics[metric], label=agent_id, linewidth=2, marker='o', markersize=3)
        ax.set_title(f"{metric.capitalize()} Over Time", fontsize=11, fontweight='bold')
        ax.set_ylabel(metric.capitalize())
        ax.grid(True, alpha=0.3)
        if idx == 0:
            ax.legend(fontsize=8)
    
    # Radar chart (bottom left)
    ax_radar = fig.add_subplot(gs[1, 0], projection='polar')
    agent_stats = {
        perf.agent_id: {
            'Health': perf.health,
            'Morale': perf.morale * 100,
            'Energy': perf.energy
        }
        for perf in agent_performances
    }
    
    labels = list(next(iter(agent_stats.values())).keys())
    num_vars = len(labels)
    angles = [n / float(num_vars) * 2 * 3.14159 for n in range(num_vars)]
    angles += angles[:1]
    
    for (agent_id, stats), color in zip(agent_stats.items(), colors):
        values = list(stats.values()) + [list(stats.values())[0]]
        ax_radar.plot(angles, values, 'o-', linewidth=2, label=agent_id, color=color)
        ax_radar.fill(angles, values, alpha=0.15, color=color)
    
    ax_radar.set_xticks([a for a in angles[:-1]])
    ax_radar.set_xticklabels(labels, fontsize=10)
    ax_radar.set_ylim(0, 105)
    ax_radar.set_title("Agent Capabilities", fontsize=11, fontweight='bold', pad=15)
    ax_radar.legend(loc='upper right', bbox_to_anchor=(1.15, 1.0), fontsize=8)
    ax_radar.grid(True)
    
    # Summary table (bottom middle & right)
    ax_table = fig.add_subplot(gs[1, 1:])
    ax_table.axis('off')
    
    table_data = []
    for perf in agent_performances:
        table_data.append([
            perf.agent_id,
            f"{perf.health:.1f}%",
            f"{perf.morale:.2f}",
            f"{perf.energy:.1f}%",
            f"{perf.total_reward:.2f}",
            str(perf.objectives_completed)
        ])
    
    table = ax_table.table(
        cellText=table_data,
        colLabels=['Agent', 'Health', 'Morale', 'Energy', 'Reward', 'Objectives'],
        cellLoc='center',
        loc='center',
        colWidths=[0.12, 0.12, 0.12, 0.12, 0.12, 0.12]
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 2)
    
    # Style header row
    for i in range(6):
        table[(0, i)].set_facecolor('#40466e')
        table[(0, i)].set_text_props(weight='bold', color='white')
    
    # Alternate row colors
    for i in range(1, len(table_data) + 1):
        for j in range(6):
            if i % 2 == 0:
                table[(i, j)].set_facecolor('#f0f0f0')
            else:
                table[(i, j)].set_facecolor('#ffffff')
    
    logger.debug("Agent performance dashboard created successfully")
    return fig


def create_training_analysis_dashboard(
    training_history: Dict[str, List[float]],
    test_performance: Dict[str, float],
    agent_stats: Dict[str, Dict[str, float]],
    figsize: Tuple[int, int] = (16, 10),
    title: str = "Training Analysis Dashboard"
) -> Figure:
    """
    Create a comprehensive training analysis dashboard.
    
    Includes:
    - Learning curves with moving averages
    - Final test performance comparison
    - Agent capabilities radar
    
    Args:
        training_history: Dict mapping agent_id to list of episode rewards
        test_performance: Dict mapping agent_id to test performance
        agent_stats: Dict mapping agent_id to stats dict
        figsize: Figure size tuple
        title: Dashboard title
        
    Returns:
        Matplotlib Figure object
    """
    logger.info("Creating training analysis dashboard")
    
    fig = plt.figure(figsize=figsize)
    fig.suptitle(title, fontsize=16, fontweight='bold', y=0.98)
    
    gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)
    
    # Learning curves (top left)
    ax_learning = fig.add_subplot(gs[0, 0])
    colors = plt.cm.Set2(range(len(training_history)))
    
    for (agent_id, history), color in zip(training_history.items(), colors):
        # Raw data
        ax_learning.plot(history, alpha=0.2, color=color, linewidth=0.5)
        # Moving average
        window = max(1, len(history) // 20)
        import numpy as np
        moving_avg = np.convolve(history, np.ones(window)/window, mode='valid')
        ax_learning.plot(moving_avg, label=f"{agent_id}", linewidth=2.5, color=color)
    
    ax_learning.set_title("Learning Curves", fontsize=12, fontweight='bold')
    ax_learning.set_xlabel("Episode")
    ax_learning.set_ylabel("Episode Reward")
    ax_learning.grid(True, alpha=0.3)
    ax_learning.legend(fontsize=10)
    
    # Test performance (top right)
    ax_test = fig.add_subplot(gs[0, 1])
    agents = list(test_performance.keys())
    performance = list(test_performance.values())
    colors_bar = plt.cm.Greens([(p - min(performance)) / (max(performance) - min(performance)) for p in performance])
    bars = ax_test.bar(agents, performance, color=colors_bar, edgecolor='black', linewidth=1.5)
    for bar in bars:
        height = bar.get_height()
        ax_test.text(bar.get_x() + bar.get_width()/2., height, f'{height:.2f}',
                    ha='center', va='bottom', fontsize=10, fontweight='bold')
    ax_test.set_title("Test Performance", fontsize=12, fontweight='bold')
    ax_test.set_ylabel("Performance Score")
    ax_test.grid(axis='y', alpha=0.3)
    
    # Capabilities radar (bottom left)
    ax_radar = fig.add_subplot(gs[1, 0], projection='polar')
    labels = list(next(iter(agent_stats.values())).keys())
    num_vars = len(labels)
    angles = [n / float(num_vars) * 2 * 3.14159 for n in range(num_vars)]
    angles += angles[:1]
    
    for agent_id, stats in agent_stats.items():
        values = list(stats.values()) + [list(stats.values())[0]]
        ax_radar.plot(angles, values, 'o-', linewidth=2, label=agent_id)
        ax_radar.fill(angles, values, alpha=0.15)
    
    ax_radar.set_xticks([a for a in angles[:-1]])
    ax_radar.set_xticklabels(labels, fontsize=10)
    ax_radar.set_ylim(0, max(max(v) for s in agent_stats.values() for v in s.values()) * 1.1)
    ax_radar.set_title("Agent Capabilities", fontsize=12, fontweight='bold', pad=20)
    ax_radar.legend(loc='upper right', bbox_to_anchor=(1.2, 1.0), fontsize=10)
    ax_radar.grid(True)
    
    # Training summary (bottom right)
    ax_summary = fig.add_subplot(gs[1, 1])
    ax_summary.axis('off')
    
    summary_text = "Training Summary\n" + "="*40 + "\n\n"
    
    for agent_id in training_history.keys():
        history = training_history[agent_id]
        import numpy as np
        summary_text += f"{agent_id}:\n"
        summary_text += f"  Episodes: {len(history)}\n"
        summary_text += f"  Best: {max(history):.2f}\n"
        summary_text += f"  Avg: {np.mean(history):.2f}\n"
        summary_text += f"  Final: {history[-1]:.2f}\n"
        if agent_id in test_performance:
            summary_text += f"  Test: {test_performance[agent_id]:.2f}\n"
        summary_text += "\n"
    
    ax_summary.text(0.1, 0.95, summary_text, transform=ax_summary.transAxes,
                   fontsize=10, verticalalignment='top', family='monospace',
                   bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.5))
    
    logger.debug("Training analysis dashboard created successfully")
    return fig


# ============================================================================
# Multi-Figure Visualization Suites
# ============================================================================

def create_complete_mission_analysis(
    reward_history: Dict[str, List[float]],
    metrics_history: Dict[str, Dict[str, List[float]]],
    agent_stats: Dict[str, Dict[str, float]],
    final_rewards: Dict[str, float],
    trajectories: Optional[Dict[str, List[Tuple[float, float]]]] = None,
    output_dir: Optional[str] = None
) -> Dict[str, Figure]:
    """
    Create a complete set of mission analysis visualizations.
    
    Includes all relevant charts, dashboards, and tables for comprehensive
    mission analysis.
    
    Args:
        reward_history: Dict mapping agent_id to reward list
        metrics_history: Dict mapping agent_id to metrics dict
        agent_stats: Dict mapping agent_id to stats dict
        final_rewards: Dict mapping agent_id to final reward
        trajectories: Optional dict of agent trajectories for GIF generation
        output_dir: Optional directory to save all figures
        
    Returns:
        Dictionary of all generated figures keyed by name
    """
    logger.info("Creating complete mission analysis suite")
    
    figures = {}
    
    # Create all visualizations
    logger.debug("Generating mission performance dashboard...")
    figures['mission_performance'] = create_mission_performance_dashboard(
        reward_history, agent_stats, final_rewards
    )
    
    logger.debug("Generating performance metrics chart...")
    from src.utils.visualizations import create_performance_metrics_chart
    figures['performance_metrics'] = create_performance_metrics_chart(metrics_history)
    
    logger.debug("Generating final rewards chart...")
    figures['final_rewards'] = create_final_rewards_bar_chart(final_rewards)
    
    logger.debug("Generating agent capabilities radar...")
    figures['capabilities_radar'] = create_agent_capabilities_radar(agent_stats)
    
    logger.info(f"Created {len(figures)} figures successfully")
    
    if output_dir:
        logger.info(f"Saving figures to {output_dir}")
        from pathlib import Path
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        from src.utils.visualizations import save_figure
        for name, fig in figures.items():
            filepath = output_path / f"{name}.png"
            save_figure(fig, str(filepath))
    
    return figures
