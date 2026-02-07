import urllib.request
import json
import os
from dotenv import load_dotenv

load_dotenv()

url = "http://localhost:8000/execute"
payload = {
    "agent_config": {},
    "auth_requirements": {},
    "env": {
        "reddit_client_id": os.getenv("REDDIT_CLIENT_ID"),
        "reddit_client_secret": os.getenv("REDDIT_CLIENT_SECRET"),
        "reddit_user_agent": os.getenv(
            "REDDIT_USER_AGENT", "python:agents-ai-python:v0.1.0 (by /u/developer)"
        ),
    },
    "inputs": {
        "query": "hiring AI agents",
        "target_subreddits": ["ArtificialInteligence"],
        # "target_subreddits": ["test"], # faster/safer if just testing logic, but AI sub exists
        "max_users": 1,
        "min_intent_score": 0.1,
    },
}

print(f"Sending request to {url}...")
# print(json.dumps(payload, indent=2))

data = json.dumps(payload).encode("utf-8")
headers = {"Content-Type": "application/json"}
req = urllib.request.Request(url, data, headers)

try:
    with urllib.request.urlopen(req) as response:
        print(f"Status: {response.getcode()}")
        body = response.read().decode("utf-8")
        try:
            print(json.dumps(json.loads(body), indent=2))
        except:
            print(body)
except urllib.error.HTTPError as e:
    print(f"HTTP Error: {e.code} {e.reason}")
    print(e.read().decode("utf-8"))
except Exception as e:
    print(f"Error: {e}")
