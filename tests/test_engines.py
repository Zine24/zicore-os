import pytest
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.app.engines.engine_a import DeterministicEngine
from backend.app.engines.engine_b import MLEngine
from backend.app.piplines.orchestrator import PipelineOrchestrator

class TestDeterministicEngine:
    @pytest.mark.asyncio
    async def test_infer_zinav(self):
        e = DeterministicEngine()
        r = await e.infer("zinav", "check orbit", "alt_km=400")
        assert r.engine == "engine_a"
        assert r.confidence >= 0.5
        assert len(r.output) > 0

    @pytest.mark.asyncio
    async def test_infer_zihab(self):
        e = DeterministicEngine()
        r = await e.infer("zihab", "check habitat", "o2=20.5")
        assert r.engine == "engine_a"

    @pytest.mark.asyncio
    async def test_infer_unknown_module(self):
        e = DeterministicEngine()
        r = await e.infer("unknown", "test", "")
        assert r.confidence == 0.6

class TestMLEngine:
    @pytest.mark.asyncio
    async def test_mock_infer_zinav(self):
        e = MLEngine()
        r = await e.infer("zinav", "check orbit", "alt_km=400")
        assert r.engine == "engine_b"
        assert "Analisis" in r.output or "ML" in r.output

    @pytest.mark.asyncio
    async def test_mock_infer_all_modules(self):
        e = MLEngine()
        for mod in ["zinav","zihab","zipower","ziship","zidrone","zirobot",
                     "zicomm","zieco","zimed","zicorex","zilink","zivr",
                     "zisec","zicriogen","zimaury","ziaxis","zty"]:
            r = await e.infer(mod, "check status", "")
            assert r.engine == "engine_b", f"Module {mod} failed"

    @pytest.mark.asyncio
    async def test_load_model_no_path(self):
        e = MLEngine()
        result = await e.load_model()
        assert result == False
        assert e.model_loaded == False

class TestOrchestrator:
    @pytest.mark.asyncio
    async def test_infer_zinav(self):
        o = PipelineOrchestrator()
        r = await o.infer("zinav", "check orbit", "alt_km=400")
        assert "engine_a" in r
        assert "engine_b" in r
        assert "merged" in r
        assert r["consensus"] in [True, False]
        assert 0 <= r["merged"]["confidence"] <= 1

    @pytest.mark.asyncio
    async def test_infer_all_modules(self):
        o = PipelineOrchestrator()
        for mod in ["zinav","zihab","zipower","ziship","zidrone"]:
            r = await o.infer(mod, "check status", f"module={mod}")
            assert "merged" in r
            assert r["merged"]["engine_used"] in ["a", "b"]

    @pytest.mark.asyncio
    async def test_confidence_merge_weights(self):
        o = PipelineOrchestrator()
        r = await o.infer("zinav", "test", "")
        m = r["merged"]
        # Weighted: A*0.6 + B*0.4
        a_conf = r["engine_a"]["confidence"]
        b_conf = r["engine_b"]["confidence"]
        expected = round(a_conf * 0.6 + b_conf * 0.4, 3)
        assert abs(m["confidence"] - expected) < 0.01

    @pytest.mark.asyncio
    async def test_zty_inference(self):
        o = PipelineOrchestrator()
        r = await o.infer("zty", "analyze blackvanta template", "name=blackvanta")
        assert "merged" in r
