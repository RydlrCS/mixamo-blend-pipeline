"""Tests for NPC engine."""
import pytest
from src.npc_engine import NPCEngine

class TestBasic:
    def test_engine_init(self):
        engine = NPCEngine()
        assert engine is not None
    
    def test_agent_register(self):
        engine = NPCEngine()
        assert engine.register_agent("a1", "scout")
