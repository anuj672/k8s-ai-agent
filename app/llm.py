import json
import os
from pathlib import Path
from pydantic import ValidationError

from app.schemas import Diagnosis
import boto3

MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "global.anthropic.claude-haiku-4-5-20251001-v1:0")
REGION = os.environ.get("AWS_REGION", "us-east-1")

GUARDRAIL_ID = os.environ.get("BEDROCK_GUARDRAIL_ID")
GUARDRAIL_VERSION = os.environ.get("BEDROCK_GUARDRAIL_VERSION", "1")
print(f"[llm] guardrail={GUARDRAIL_ID} version={GUARDRAIL_VERSION}")


class GuardrailBlocked(Exception):
    """Raised when Bedrock Guardrails blocks the request (e.g. prompt injection)."""

# Load the prompt once at startup (prompts as code)
SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / "system.md").read_text()

_client = boto3.client("bedrock-runtime", region_name=REGION)



def diagnose(evidence: dict) -> tuple[Diagnosis, dict]:
    evidence_text = json.dumps(evidence, default=str)

    # guardContent marks ONLY the evidence as untrusted input for the guardrail,
    # so our own system prompt is never mistaken for an attack.
    evidence_block = (
        {"guardContent": {"text": {"text": evidence_text}}}
        if GUARDRAIL_ID
        else {"text": evidence_text}
    )

    request = {
        "modelId": MODEL_ID,
        "system": [{"text": SYSTEM_PROMPT}],
        "messages": [{
            "role": "user",
            "content": [{"text": "Evidence collected from the cluster:"}, evidence_block],
        }],
        "inferenceConfig": {"maxTokens": 2000, "temperature": 0},
    }
    if GUARDRAIL_ID:
        request["guardrailConfig"] = {
            "guardrailIdentifier": GUARDRAIL_ID,
            "guardrailVersion": GUARDRAIL_VERSION,
            "trace": "enabled",
        }

    response = _client.converse(**request)

    if response.get("stopReason") == "guardrail_intervened":
        raise GuardrailBlocked(
            "Blocked by Bedrock Guardrails: possible prompt injection in cluster evidence (logs/events)."
        )

    text = response["output"]["message"]["content"][0]["text"]
    return _validate(text), response["usage"]

def _validate(text: str) -> Diagnosis:
    try:
        return Diagnosis.model_validate(_parse_json(text))
    except ValidationError as e:
        raise ValueError(f"Model output failed schema validation: {e.errors()[:3]}")
    
def _parse_json(text: str) -> dict:
    text = text.strip()
    # Models sometimes wrap JSON in ```json fences despite instructions
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        raise ValueError(f"Model did not return valid JSON: {text[:200]}")