"""Counterfactual fairness: identity never changes a pathway (handbook good-to-have)."""

from fastapi.testclient import TestClient

from app.core.fairness import counterfactual_diffs
from app.features.pathway import engine, service
from app.features.profile import repository

SKILLS = {"excel": 4, "process-mapping": 2}


def _learner(**overrides: object) -> engine.Learner:
    base: dict[str, object] = {
        "skill_levels": SKILLS,
        "hours_per_week": 6.0,
        "budget_myr": 500.0,
        "hrd_eligible": True,
    }
    return engine.Learner(**{**base, **overrides})  # type: ignore[arg-type]


def _plan_key(learner: engine.Learner) -> object:
    plan = service.build_pathway(learner, "process-automation-analyst", "fast")
    return [(s.skill_id, [c.id for c in s.courses], s.week_start, s.week_end) for s in plan.steps]


def test_learner_input_has_no_identity_fields() -> None:
    assert set(engine.Learner.__dataclass_fields__) == {
        "skill_levels",
        "hours_per_week",
        "budget_myr",
        "hrd_eligible",
    }


def test_identical_profiles_get_identical_pathways_end_to_end(client: TestClient) -> None:
    """Give three different personas the same skills, hours and budget via the API."""
    originals = {uid: repository.get_profile(uid) for uid in ("aisyah", "weijie", "ravi")}
    profile = {
        "segment": "working",
        "interests": ["data"],
        "hours_per_week": 6,
        "budget_myr": 500,
        "hrd_eligible": True,
    }
    skills = [{"skill_id": k, "level": v, "source": "confirmed"} for k, v in SKILLS.items()]
    try:
        keys: dict[str, object] = {}
        for uid, segment in (("aisyah", "working"), ("weijie", "graduate"), ("ravi", "switcher")):
            headers = {"X-Demo-User": uid}
            # Segment differs on purpose: it changes intake questions, never the plan.
            client.post("/api/v1/profile", json={**profile, "segment": segment}, headers=headers)
            client.put("/api/v1/profile/skills", json={"skills": skills}, headers=headers)
            body = client.get(
                "/api/v1/pathway",
                params={"role_id": "process-automation-analyst", "scenario": "fast"},
                headers=headers,
            ).json()
            keys[uid] = [(s["skill_id"], [c["id"] for c in s["courses"]]) for s in body["steps"]]
        assert keys["aisyah"] == keys["weijie"] == keys["ravi"]
    finally:
        for p in originals.values():
            if p is not None:
                repository.save_profile(p)


def test_counterfactual_helper_on_real_engine() -> None:
    base = _learner()
    variants = {"budget-equal-copy": _learner(), "hrd-same": _learner(hrd_eligible=True)}
    assert counterfactual_diffs(_plan_key, base, variants) == []
    # Sanity check: inputs that *should* matter do change the plan.
    assert counterfactual_diffs(_plan_key, base, {"fewer-hours": _learner(hours_per_week=1.0)})
