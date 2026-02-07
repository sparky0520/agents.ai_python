# Complete Implementation: RedditJPLearningDemandScout

This document shows the complete implementation of an AI agent marketplace from three perspectives:
1. **Publisher**: What they create and upload
2. **System**: How the marketplace executes the agent  
3. **User**: What they see and receive

---

## PART 1: PUBLISHER PERSPECTIVE

### What the Publisher Creates

The publisher creates a package with these files:

#### 1. `agent.yaml` - Agent Specification
```yaml
name: RedditJPLearningDemandScout
version: 1.0.0
runtime: openclaw
category: market_research
author: demo_publisher

description: |
  Identifies Reddit users who show intent to learn Japanese and demonstrate 
  willingness to pay for an app or learning resource.

inputs:
  - name: max_users
    type: integer
    default: 20
    description: Maximum number of candidates to find

  - name: min_intent_score
    type: float
    default: 0.7
    description: Minimum intent score threshold (0.0-1.0)

outputs:
  - name: candidates
    type: json
    schema_file: schemas/output.json

pricing:
  model: per_execution
  base_cost: 5.00
  currency: USD

requirements:
  mcp_servers:
    - reddit-search-mcp
  max_iterations: 20
  timeout_minutes: 10
```

#### 2. `controller.txt` - System Prompt
The controller prompt defines agent behavior, intent scoring rubric (0.7-1.0), and execution guidelines.

#### 3. `schemas/output.json` - Output Schema
Defines the JSON structure for results with candidates array and summary object.

#### 4. `mcp-server/reddit-search.js` - MCP Server
Implements four tools:
- `search_reddit(query, subreddit, limit)` - Search for posts
- `get_thread(thread_url)` - Read thread content
- `get_comments(thread_url, limit)` - Extract comments
- `store_candidate(...)` - Track qualified users

### Publishing Process

```bash
# Validate package
marketplace validate ./agent-package

# Test locally
marketplace test ./agent-package --dry-run

# Publish to marketplace
marketplace publish ./agent-package
```

---

## PART 2: SYSTEM PERSPECTIVE (Orchestration)

### When User Clicks "Hire Agent"

#### Step 1: Load Agent Specification
```python
# Load agent.yaml
agent_spec = load_yaml('/marketplace/agents/reddit-jp/agent.yaml')

# Validate inputs
validate_inputs(user_inputs, agent_spec['inputs'])

# Check MCP server availability
ensure_mcp_servers(agent_spec['requirements']['mcp_servers'])
```

#### Step 2: Create Execution Session
```python
session = ExecutionSession(
    session_id=generate_id(),
    agent_spec=agent_spec,
    user_inputs={'max_users': 15, 'min_intent_score': 0.7},
    status='pending'
)
```

#### Step 3: Initialize Callbacks
```python
callbacks = [
    WebSocketCallback(ws),        # Real-time UI updates
    LogCallback(db),               # Audit trail
    CostTrackerCallback(),         # Bill tracking
    MonitoringCallback(limits),    # Safety limits
    ProgressAggregatorCallback()   # Statistics
]
```

#### Step 4: Start Orchestration Loop
```python
# For each iteration:
while not should_stop(session):
    # Search Reddit
    results = await mcp_tools.search_reddit(query, subreddit, limit=5)
    
    # Analyze each thread
    for thread in results:
        comments = await mcp_tools.get_comments(thread['url'])
        
        # Score intent
        for comment in comments:
            score = analyze_intent(comment['text'])
            
            if score >= min_intent_score:
                # Store candidate
                await mcp_tools.store_candidate(
                    username=comment['author'],
                    intent_score=score,
                    evidence=[comment['text']],
                    ...
                )
                
                # Emit progress update
                await emit_progress(ProgressUpdate(
                    type='finding',
                    message=f'Found: {username} (score: {score})',
                    data={'total_candidates': count}
                ))
    
    # Check stopping conditions
    if candidates_found >= max_users:
        break
    if diminishing_returns():
        break
```

#### Step 5: Format and Validate Output
```python
output = {
    "results": candidates_list,
    "summary": {
        "total_users": len(candidates),
        "high_confidence_users": count_high,
        "observed_patterns": extract_patterns(),
        ...
    }
}

# Validate against schema
validate_schema(output, schemas/output.json)

# Store in database
db.save_result(session_id, output)
```

### Real-time Callbacks in Action

#### WebSocket Updates to User

```javascript
// Iteration started
{
  "type": "iteration",
  "message": "Starting iteration 3/20",
  "data": {"iteration": 3, "candidates_found": 5}
}

// Tool call
{
  "type": "tool_call", 
  "message": "Searching r/LearnJapanese",
  "data": {"tool": "search_reddit", "subreddit": "LearnJapanese"}
}

// Finding
{
  "type": "finding",
  "message": "Found: u/serious_student_88 (score: 0.95)",
  "data": {"username": "u/serious_student_88", "total_candidates": 6}
}

// Completion
{
  "type": "status",
  "message": "Agent completed successfully",
  "data": {"candidates_found": 12, "execution_time": 45.3, "cost": 5.00}
}
```

---

## PART 3: USER PERSPECTIVE

### User Journey

#### 1. Browse Marketplace

```
┌─────────────────────────────────────────────────────────────┐
│ MARKETPLACE - MARKET RESEARCH                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ 📦 RedditJPLearningDemandScout                             │
│    ⭐⭐⭐⭐⭐ 4.8 (23 runs)                                │
│                                                             │
│    Identifies Reddit users willing to pay for Japanese      │
│    learning apps. Returns scored candidates with evidence.  │
│                                                             │
│    💰 $5.00 per execution                                  │
│    ⏱️ Est. time: 5-10 minutes                              │
│    🏷️ reddit • market-research • japanese                  │
│                                                             │
│    [View Details] [Run Agent]                              │
└─────────────────────────────────────────────────────────────┘
```

#### 2. Configure Agent

```
┌─────────────────────────────────────────────────────────────┐
│ CONFIGURE AGENT                                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Maximum candidates: [20 ▼]                                 │
│ Min intent score:   [0.7 ━━━━━━━●─] 0.7                   │
│                                                             │
│ Estimated cost: $5.00                                       │
│                                                             │
│ [Cancel] [Run Agent]                                        │
└─────────────────────────────────────────────────────────────┘
```

#### 3. Watch Live Progress

```
┌─────────────────────────────────────────────────────────────┐
│ AGENT RUNNING                                               │
│ Session: session_abc123 • Cost: $5.00                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ ⏳ Progress: Iteration 5/20                                 │
│                                                             │
│ ✓ Searched r/LearnJapanese (14 threads)                    │
│ ✓ Searched r/Japanese (8 threads)                          │
│ ⏳ Searching r/languagelearning...                          │
│                                                             │
│ ⭐ Found 8 candidates:                                      │
│    • u/serious_student_88 (0.95)                            │
│    • u/professional_need (0.88)                             │
│    • u/time_limited (0.85)                                  │
│    • 5 more...                                              │
│                                                             │
│ 📊 Stats: 23 threads analyzed • 42 tool calls               │
│                                                             │
│ Est. completion: 3 min                                      │
└─────────────────────────────────────────────────────────────┘
```

#### 4. View Results

```
┌─────────────────────────────────────────────────────────────┐
│ ✅ EXECUTION COMPLETE                                       │
│ Time: 5 min 23s • Cost: $5.00                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ 📊 SUMMARY                                                  │
│    Total candidates: 12                                     │
│    High confidence (≥0.85): 8                               │
│    Threads analyzed: 35                                     │
│    Iterations: 8                                            │
│                                                             │
│ 🔍 KEY INSIGHTS                                             │
│    • Frustration with overly gamified apps                  │
│    • Desire for conversation/speaking practice              │
│    • Free apps perceived as insufficient                    │
│                                                             │
│ 📍 TOP SUBREDDITS                                           │
│    • r/LearnJapanese: 7 candidates                          │
│    • r/languagelearning: 3 candidates                       │
│    • r/Japanese: 2 candidates                               │
│                                                             │
└─────────────────────────────────────────────────────────────┘

👥 QUALIFIED CANDIDATES

1. u/serious_student_88
   Intent Score: 0.95 ⭐⭐⭐⭐⭐
   Subreddit: r/LearnJapanese
   Thread: Looking for paid Japanese learning app recommendations
   
   Evidence:
   💬 "I'd happily pay $30/month for an app that focuses on 
       actual conversation skills. Most apps are too gamified."
   
   🔗 [View Thread]
   ──────────────────────────────────────────────────────────

2. u/professional_need  
   Intent Score: 0.88 ⭐⭐⭐⭐
   Subreddit: r/LearnJapanese
   Thread: Free vs paid Japanese learning resources
   
   Evidence:
   💬 "I need something more professional and structured. 
       Free apps feel like toys. Willing to invest."
   
   🔗 [View Thread]
   ──────────────────────────────────────────────────────────

... and 10 more candidates

[Download JSON] [Export CSV] [Share] [Run Again]
```

#### 5. Export Data

User downloads results in multiple formats:

**output.json** - Structured data for developers
**output.csv** - Spreadsheet for analysis
**output.md** - Human-readable report

---

## KEY IMPLEMENTATION DETAILS

### Intent Scoring (Simplified Heuristic in Demo)

```python
def analyze_intent(text: str) -> float:
    text_lower = text.lower()
    
    # 0.9-1.0: Explicit willingness to pay
    if any(phrase in text_lower for phrase in [
        "i'd pay", "willing to pay", "happily pay"
    ]):
        return 0.95
    
    # 0.7-0.85: Strong dissatisfaction with free options
    if any(phrase in text_lower for phrase in [
        "paid alternative", "free apps aren't", "invest in"
    ]):
        return 0.80
    
    # <0.7: Insufficient evidence (not included)
    return 0.3
```

### Deduplication

```python
# Track candidates by username
if username in candidates:
    continue  # Skip duplicate

candidates[username] = {...}
```

### Stopping Conditions

```python
# Stop if:
if len(candidates) >= max_users:
    break  # Reached target
    
if iteration > 5 and len(candidates) < iteration * 0.5:
    break  # Diminishing returns

if iteration >= max_iterations:
    break  # Safety limit
```

---

## FILE LOCATIONS

All implementation files are located at:

```
/home/claude/agent-package/          # Publisher's package
├── agent.yaml                       # Agent specification
├── controller.txt                   # System prompt
├── schemas/output.json              # Output schema
├── mcp-server/reddit-search.js      # MCP implementation
└── README.md                        # Publisher guide

/home/claude/marketplace-system/     # System orchestration
├── orchestrator.py                  # Execution engine
├── callbacks.py                     # Real-time updates
├── mcp_tools.py                     # Tool implementations
└── user_interface.py                # UI components
```

---

## SUMMARY

**Publisher** creates:
- Agent spec (YAML)
- Controller prompt (TXT)
- MCP server (JS)
- Output schema (JSON)

**System** provides:
- Orchestration engine (OpenClaw-style)
- Real-time callbacks (WebSocket, logging, cost tracking)
- MCP tool execution
- Output validation

**User** receives:
- Live progress updates
- Structured results with evidence
- Multiple export formats
- Cost transparency

This creates a complete marketplace where publishers build once, the system executes reliably, and users get predictable, high-quality results.
