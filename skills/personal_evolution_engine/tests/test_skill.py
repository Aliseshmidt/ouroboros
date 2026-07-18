from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from skills.personal_evolution_engine.engine import (
    PersonalAutomationEngine,
    _directory_digest,
)

SKILL_DIR = Path(__file__).resolve().parents[1]


class FakeAPI:
    def __init__(self, state_dir: Path) -> None:
        self.state_dir = state_dir

    def get_runtime_info(self) -> dict[str, str]:
        return {"skill_dir": str(SKILL_DIR)}

    def get_state_dir(self) -> str:
        return str(self.state_dir)

    def skill_job_dir(self, job_id: str) -> Path:
        root = self.state_dir / "jobs" / job_id
        for child in ("assets", "output", "tmp"):
            (root / child).mkdir(parents=True, exist_ok=True)
        return root


class PersonalAutomationSkillTests(unittest.TestCase):
    def _engine(self, state_dir: Path) -> PersonalAutomationEngine:
        return PersonalAutomationEngine(FakeAPI(state_dir))

    def _approve_current(self, engine: PersonalAutomationEngine, state_dir: Path) -> None:
        verification = engine.verify_automation(show_each_check=True)
        self.assertIn("точность 100%", verification)
        state = json.loads((state_dir / "automation_state.json").read_text(encoding="utf-8"))
        confirmation = state["current"]["confirmation_phrase"]
        self.assertIn("Подтверждение принято", engine.approve_automation(confirmation=confirmation))

    def test_discovery_is_derived_from_activity_data(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            engine = self._engine(Path(raw_dir))
            message = engine.observe_work(maximum_suggestions=5)
            state = json.loads((Path(raw_dir) / "automation_state.json").read_text(encoding="utf-8"))
            self.assertIn("239 действий", message)
            self.assertEqual(5, len(state["candidates"]))
            self.assertTrue(all(candidate["occurrences"] >= 12 for candidate in state["candidates"]))
            self.assertTrue(all(candidate["recipe"] for candidate in state["candidates"]))

    def test_explicit_confirmation_is_required(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            state_dir = Path(raw_dir)
            engine = self._engine(state_dir)
            engine.observe_work()
            engine.prepare_automation(choice="1")
            engine.verify_automation()
            self.assertIn("не совпало", engine.approve_automation(confirmation="Да"))
            self.assertIn("нужна точная фраза", engine.run_automation())

    def test_every_discovered_workflow_creates_a_real_result_and_rolls_back(self) -> None:
        expected_suffixes = [".xlsx", ".pptx", ".eml", ".json", ".xlsx"]
        source_dir = SKILL_DIR / "assets" / "synthetic" / "workspace"
        source_digest = _directory_digest(source_dir)
        for choice, suffix in enumerate(expected_suffixes, 1):
            with self.subTest(choice=choice), tempfile.TemporaryDirectory() as raw_dir:
                state_dir = Path(raw_dir)
                engine = self._engine(state_dir)
                engine.observe_work(maximum_suggestions=5)
                prepared = engine.prepare_automation(choice=str(choice))
                self.assertIn("подготовила личную автоматизацию", prepared)
                self._approve_current(engine, state_dir)
                completed = engine.run_automation()
                self.assertIn("Готово", completed)
                state = json.loads((state_dir / "automation_state.json").read_text(encoding="utf-8"))
                output_dir = Path(state["runs"][-1]["output_dir"])
                artifacts = [path for path in output_dir.rglob("*") if path.is_file()]
                self.assertTrue(any(path.suffix == suffix for path in artifacts))
                self.assertEqual(source_digest, _directory_digest(source_dir))
                self.assertIn("Откат завершён", engine.rollback_automation())
                self.assertFalse(output_dir.exists())

    def test_feedback_changes_future_ranking_without_mutating_current_recipe(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            state_dir = Path(raw_dir)
            engine = self._engine(state_dir)
            engine.observe_work(maximum_suggestions=5)
            engine.prepare_automation(choice="5")
            before = json.loads((state_dir / "automation_state.json").read_text(encoding="utf-8"))
            current_key = before["current"]["candidate_key"]
            current_recipe = next(item["recipe"] for item in before["candidates"] if item["key"] == current_key)
            self.assertIn("более высокий приоритет", engine.record_feedback(outcome="accepted"))
            after_feedback = json.loads((state_dir / "automation_state.json").read_text(encoding="utf-8"))
            self.assertEqual(current_recipe, next(
                item["recipe"] for item in after_feedback["candidates"] if item["key"] == current_key
            ))
            engine.observe_work(maximum_suggestions=5)
            after_observation = json.loads((state_dir / "automation_state.json").read_text(encoding="utf-8"))
            reranked = next(item for item in after_observation["candidates"] if item["key"] == current_key)
            self.assertGreater(reranked["ranking_score"], before["candidates"][-1]["ranking_score"])


if __name__ == "__main__":
    unittest.main()
