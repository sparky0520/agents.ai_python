from reddit_scout import AgentInputs
import json

schema = AgentInputs.model_json_schema()
print(json.dumps(schema, indent=2))
