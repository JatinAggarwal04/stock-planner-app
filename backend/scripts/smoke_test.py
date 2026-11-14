"""Smoke test run inside the built Docker image (see .github/workflows/ci.yml).

Checks that the production image can import the app (xgboost + torch together),
load the baked-in FinBERT model without downloading it, and score headlines.
"""
import asyncio
import os

os.environ["HF_HUB_OFFLINE"] = "1"  # the model must already be in the image

import main

result = asyncio.run(main.SentimentAnalyzer().analyze_finbert([
    "Company beats quarterly profit estimates and raises guidance",
    "Shares plunge after weak results and margin pressure",
]))
print("FinBERT result:", result)
assert result["breakdown"]["positive"] + result["breakdown"]["negative"] + result["breakdown"]["neutral"] == 2
assert result["confidence"] > 0
print("Smoke test passed")
