import os

import boto3

MODEL_ID = os.environ["BEDROCK_MODEL_ID"]
client = boto3.client("bedrock-runtime", region_name="us-east-1")

response = client.converse(
    modelId=MODEL_ID,
    messages=[{"role": "user", "content": [{"text": "Reply with exactly: ok"}]}],
    inferenceConfig={"maxTokens": 10},
)
print(response["output"]["message"]["content"][0]["text"])