"""
Tests for ZIO Agent infrastructure
"""
import pytest
import asyncio
import json
import time


class TestAgentState:
    """Test agent state management."""

    def test_create_session(self):
        from agent.state import AgentSession, state_manager
        session = state_manager.create_session("test_001")
        assert session.id == "test_001"
        assert session.created > 0
        state_manager.delete_session("test_001")

    def test_get_or_create(self):
        from agent.state import state_manager
        s1 = state_manager.get_or_create("test_002")
        s2 = state_manager.get_or_create("test_002")
        assert s1.id == s2.id
        state_manager.delete_session("test_002")

    def test_delete_session(self):
        from agent.state import state_manager
        state_manager.create_session("test_del")
        state_manager.delete_session("test_del")
        assert state_manager.get_session("test_del") is None

    def test_list_sessions(self):
        from agent.state import state_manager
        state_manager.create_session("test_list_a")
        state_manager.create_session("test_list_b")
        sessions = state_manager.list_sessions()
        ids = [s["id"] for s in sessions]
        assert "test_list_a" in ids
        assert "test_list_b" in ids
        state_manager.delete_session("test_list_a")
        state_manager.delete_session("test_list_b")

    def test_global_status(self):
        from agent.state import state_manager
        status = state_manager.get_global_status()
        assert "active_sessions" in status
        assert "uptime" in status


class TestContextMemory:
    """Test context memory system."""

    def test_add_and_get(self):
        from agent.state import ContextMemory
        mem = ContextMemory()
        mem.add("user", "hello")
        mem.add("assistant", "hi there")
        recent = mem.get_recent(5)
        assert len(recent) == 2
        assert recent[0]["role"] == "user"
        assert recent[1]["role"] == "assistant"

    def test_overflow(self):
        from agent.state import ContextMemory
        mem = ContextMemory(max_short=10)
        for i in range(15):
            mem.add("user", f"msg_{i}")
        assert len(mem.short_term) <= 10
        assert len(mem.long_term) > 0

    def test_context_window(self):
        from agent.state import ContextMemory
        mem = ContextMemory()
        mem.add("user", "test message")
        window = mem.get_context_window()
        assert "USER" in window
        assert "test message" in window

    def test_entity_memory(self):
        from agent.state import ContextMemory
        mem = ContextMemory()
        mem.remember_entity("module", "zinav")
        assert mem.recall_entity("module") == "zinav"
        assert mem.recall_entity("nonexistent") is None

    def test_clear(self):
        from agent.state import ContextMemory
        mem = ContextMemory()
        mem.add("user", "test")
        mem.remember_entity("key", "val")
        mem.clear()
        assert len(mem.short_term) == 0
        assert len(mem.entity_memory) == 0

    def test_summarize(self):
        from agent.state import ContextMemory
        mem = ContextMemory()
        mem.add("user", "trajectory to mars")
        mem.add("assistant", "delta-v calculated")
        summary = mem.summarize()
        assert isinstance(summary, str)


class TestToolRegistry:
    """Test tool registry."""

    def test_register_and_call(self):
        from agent.state import ToolRegistry
        reg = ToolRegistry()
        reg.register("add", lambda a, b: a + b, "Add two numbers", {"a": int, "b": int})
        result = reg.call("add", a=3, b=4)
        assert result == 7

    def test_list_tools(self):
        from agent.state import ToolRegistry
        reg = ToolRegistry()
        reg.register("test_tool", lambda: None, "Test tool")
        tools = reg.list_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == "test_tool"

    def test_exists(self):
        from agent.state import ToolRegistry
        reg = ToolRegistry()
        reg.register("my_tool", lambda: None)
        assert reg.exists("my_tool")
        assert not reg.exists("other_tool")

    def test_call_unknown(self):
        from agent.state import ToolRegistry
        reg = ToolRegistry()
        with pytest.raises(ValueError):
            reg.call("nonexistent")


class TestAgentCore:
    """Test agent core functionality."""

    def test_classify_intent(self):
        from agent.core import ZICoreAgent
        agent = ZICoreAgent("test_core")
        assert agent._classify_intent("generate a 3d model") == "3d_generate"
        assert agent._classify_intent("create an image") == "image_generate"
        assert agent._classify_intent("make a video") == "video_generate"
        assert agent._classify_intent("play a sound") == "sound_generate"
        assert agent._classify_intent("calculate trajectory to moon") == "trajectory"
        assert agent._classify_intent("design a rocket") == "aircraft_design"
        assert agent._classify_intent("check system status") == "system_status"
        assert agent._classify_intent("hello world") == "general"

    def test_trajectory_calc(self):
        from agent.core import ZICoreAgent
        agent = ZICoreAgent("test_traj")
        result = agent._compute_trajectory("hohmann transfer to GEO")
        assert "delta_v_ms" in result
        assert "time_hours" in result
        assert result["type"] == "hohmann"

    def test_trajectory_lunar(self):
        from agent.core import ZICoreAgent
        agent = ZICoreAgent("test_lunar")
        result = agent._compute_trajectory("lunar transfer")
        assert result["type"] == "lunar"
        assert "time_days" in result

    def test_trajectory_mars(self):
        from agent.core import ZICoreAgent
        agent = ZICoreAgent("test_mars")
        result = agent._compute_trajectory("mars mission")
        assert result["type"] == "mars"

    def test_design_aircraft(self):
        from agent.core import ZICoreAgent
        agent = ZICoreAgent("test_design")
        result = agent._design_aircraft("build a reusable rocket")
        assert "stages" in result
        assert "propulsion" in result
        assert result["propulsion"]["engine_count"] >= 7

    def test_capabilities(self):
        from agent.core import ZICoreAgent
        agent = ZICoreAgent("test_caps")
        caps = agent.get_capabilities()
        assert len(caps) > 10
        assert any("3D" in c for c in caps)
        assert any("trajectory" in c.lower() for c in caps)

    def test_system_status(self):
        from agent.core import ZICoreAgent
        agent = ZICoreAgent("test_status")
        status = agent._get_system_status()
        assert "online" in status["agent"].lower()
        assert status["session"] == "test_status"

    def test_general_response(self):
        from agent.core import ZICoreAgent
        agent = ZICoreAgent("test_gen")
        resp = agent._general_response("hello", None)
        assert "ZIO" in resp
        assert len(resp) > 20

    def test_history(self):
        from agent.core import ZICoreAgent
        agent = ZICoreAgent("test_hist")
        agent.session.memory.add("user", "test message")
        history = agent.get_history(5)
        assert len(history) >= 1

    def test_clear_context(self):
        from agent.core import ZICoreAgent
        agent = ZICoreAgent("test_clear")
        agent.session.memory.add("user", "test")
        agent.clear_context()
        assert len(agent.session.memory.short_term) == 0


class TestAgentProcess:
    """Test agent async processing."""

    @pytest.mark.asyncio
    async def test_process_general(self):
        from agent.core import ZICoreAgent
        agent = ZICoreAgent("test_proc")
        result = await agent.process("hello world")
        assert result["intent"] == "general"
        assert "text" in result["outputs"]

    @pytest.mark.asyncio
    async def test_process_trajectory(self):
        from agent.core import ZICoreAgent
        agent = ZICoreAgent("test_traj_proc")
        result = await agent.process("calculate hohmann transfer")
        assert result["intent"] == "trajectory"
        assert "trajectory" in result["outputs"]

    @pytest.mark.asyncio
    async def test_process_aircraft(self):
        from agent.core import ZICoreAgent
        agent = ZICoreAgent("test_ac_proc")
        result = await agent.process("design a rocket")
        assert result["intent"] == "aircraft_design"
        assert "aircraft" in result["outputs"]

    @pytest.mark.asyncio
    async def test_process_3d(self):
        from agent.core import ZICoreAgent
        agent = ZICoreAgent("test_3d_proc")
        result = await agent.process("generate a 3d model of a satellite")
        assert result["intent"] == "3d_generate"

    @pytest.mark.asyncio
    async def test_process_status(self):
        from agent.core import ZICoreAgent
        agent = ZICoreAgent("test_st_proc")
        result = await agent.process("system status")
        assert result["intent"] == "system_status"
        assert "status" in result["outputs"]

    @pytest.mark.asyncio
    async def test_process_help(self):
        from agent.core import ZICoreAgent
        agent = ZICoreAgent("test_help_proc")
        result = await agent.process("help")
        assert result["intent"] == "help"
        assert "capabilities" in result["outputs"]


class TestAgentAPI:
    """Test agent API endpoints."""

    def test_api_status(self):
        from backend.app.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        r = client.get("/api/agent/status")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "online"
        assert "capabilities" in data

    def test_api_capabilities(self):
        from backend.app.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        r = client.get("/api/agent/capabilities")
        assert r.status_code == 200
        data = r.json()
        assert "engines" in data
        assert "modules" in data
        assert "multimedia" in data

    def test_api_chat(self):
        from backend.app.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        r = client.post("/api/agent/chat", json={"message": "hello", "session_id": "test_api"})
        assert r.status_code == 200
        data = r.json()
        assert data["intent"] == "general"
        assert "outputs" in data

    def test_api_chat_trajectory(self):
        from backend.app.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        r = client.post("/api/agent/chat", json={"message": "hohmann transfer", "session_id": "test_traj_api"})
        assert r.status_code == 200
        data = r.json()
        assert data["intent"] == "trajectory"

    def test_api_sessions(self):
        from backend.app.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        r = client.get("/api/agent/sessions")
        assert r.status_code == 200
        assert "sessions" in r.json()

    def test_api_inference(self):
        from backend.app.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        r = client.post("/api/agent/inference", json={"module": "zinav", "instruction": "status"})
        assert r.status_code == 200
        data = r.json()
        assert "engine_a" in data
        assert "engine_b" in data
