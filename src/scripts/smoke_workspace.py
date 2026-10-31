"""Read-only route smoke checks against a running local Compose workspace."""

from __future__ import annotations

import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    base = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:3000"
    with httpx.Client(base_url=base, timeout=30, follow_redirects=False) as client:
        deep = "/app/progress?role=data-analyst&scenario=fast"
        gate = client.get(deep)
        assert gate.status_code == 303, (gate.status_code, gate.text[:80])
        assert "next=%2Fapp%2Fprogress" in gate.headers["location"]
        for persona, paths in (
            (
                "aisyah",
                [
                    "/app",
                    "/app/onboarding",
                    "/app/profile",
                    "/app/radar",
                    "/app/matches",
                    "/app/matches/data-analyst",
                    "/app/pathway?role=data-analyst",
                    "/app/progress?role=data-analyst",
                    "/app/courses",
                    "/app/sdg?role=data-analyst",
                ],
            ),
            (
                "demo-company",
                [
                    "/org",
                    "/org/setup",
                    "/org/members",
                    "/org/radar",
                    "/org/gaps",
                    "/org/plan?role=data-analyst",
                    "/org/courses",
                    "/org/verify",
                    "/org/sdg",
                ],
            ),
        ):
            client.cookies.set("adept_demo", persona)
            for path in paths:
                response = client.get(path)
                assert response.status_code == 200, (path, response.status_code)
                assert "Application error:" not in response.text, path
                print("OK", path)
        client.cookies.clear()
        for path in ("/", "/try", "/journey", "/auth/login", "/about"):
            assert client.get(path).status_code == 200, path
        for value in ("https://evil.example/app", "//evil.example/app", "/org"):
            response = client.get("/demo/learner", params={"next": value})
            assert response.headers["location"] == "/app"
        client.cookies.clear()
        cv = ROOT / "tests/api/profile/fixtures/cvs/cv_aisyah.pdf"
        response = client.post(
            "/api/preview",
            headers={"Origin": base},
            data={"synthetic_consent": "true"},
            files={"file": ("synthetic.pdf", cv.read_bytes(), "application/pdf")},
        )
        assert response.status_code == 200, (response.status_code, response.text)
        preview = response.json()
        assert preview["top_role"] and preview["requires_skill_confirmation"]
        assert "matches" not in preview
        assert preview["meta"]["sources"]
        print("OK anonymous synthetic CV preview")
        response = client.post(
            "/api/preview",
            headers={"Origin": "https://evil.example"},
            data={"synthetic_consent": "true"},
            files={"file": ("synthetic.txt", b"Python", "text/plain")},
        )
        assert response.status_code == 403
        print("OK cross-origin upload rejected")
    print("Workspace smoke checks passed")


if __name__ == "__main__":
    main()
