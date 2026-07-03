from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app import app


RESPONSES = [
    '{"thought":{"situation_analysis":"Need broader context.","spatial_reasoning":"Unknown room layout.","task_planning":"Observe first.","self_reflection":"No strong evidence yet.","verification":"Observation is safe."},"action":{"name":"observe","argument":null,"confidence":0.9}}',
    '{"thought":{"situation_analysis":"A sofa is relevant.","spatial_reasoning":"Sofa is navigable.","task_planning":"Navigate to sofa.","self_reflection":"Direct navigation is reasonable.","verification":"Sofa is in legal navigations."},"action":{"name":"navigate to","argument":"Sofa","confidence":0.8}}',
    '{"thought":{"situation_analysis":"Task can end.","spatial_reasoning":"No more movement required.","task_planning":"End.","self_reflection":"Stop after navigation.","verification":"Terminal action chosen."},"action":{"name":"end","argument":null,"confidence":0.7}}',
]


def main() -> None:
    with TestClient(app) as client:
        client.post("/api/env/load", json={"scene": "FloorPlan211", "task": "Smoke agent loop"}).raise_for_status()
        client.post("/api/agent/reset", json={"task_instruction": "Find the sofa.", "target_object": "Sofa", "max_steps": 3}).raise_for_status()
        with patch("backend.llm.openai_compatible_client.OpenAICompatibleClient.chat", side_effect=RESPONSES):
            for _ in RESPONSES:
                response = client.post("/api/agent/step", json={"execute": True})
                response.raise_for_status()
                payload = response.json()
                print(payload["step"], payload["action"]["name"], payload["action_result"]["success"], payload["action_result"]["message"])
                if payload["action_result"]["done"]:
                    break


if __name__ == "__main__":
    main()
