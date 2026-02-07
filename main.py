from typing import TypedDict, List, Dict
from langgraph.graph import StateGraph, END
import random
import time


# --- 1. State Definition ---
class AgentState(TypedDict):
    """
    Represents the state of the Reddit Scout Agent.
    """

    query: str
    target_subreddits: List[str]
    max_users: int
    min_intent_score: float

    # Internal state
    visited_threads: List[str]  # Visited thread IDs/URLs
    candidates: List[Dict]  # List of found candidates
    threads_to_process: List[Dict]  # Threads found in the current search step
    iteration: int
    is_complete: bool


# --- 2. Mock Tools ---
def mock_search_reddit(query: str, subreddit: str, limit: int = 5) -> List[Dict]:
    """
    Simulates searching Reddit for threads.
    Returns a list of thread objects.
    """
    print(f"  [Tool] Searching r/{subreddit} for '{query}'...")
    time.sleep(0.5)  # Simulate network latency

    # Generate some mock threads
    threads = []
    titles = [
        "Best Japanese learning apps?",
        "Looking for paid conversation practice",
        "Genki vs Minna no Nihongo",
        "Is Duolingo good for N3?",
        "Willing to pay for a good tutor/app",
        "Free resources strictly",
        "Review of Bunpro",
        "Need help with Kanji",
    ]

    for i in range(limit):
        thread_id = f"{subreddit}_{random.randint(1000, 9999)}"
        title = random.choice(titles)
        threads.append(
            {
                "id": thread_id,
                "url": f"https://reddit.com/r/{subreddit}/comments/{thread_id}",
                "title": title,
                "subreddit": subreddit,
            }
        )
    return threads


def mock_get_thread_comments(thread_url: str, limit: int = 10) -> List[Dict]:
    """
    Simulates fetching comments for a thread.
    Returns a list of comment objects.
    """
    # print(f"  [Tool] Fetching comments for {thread_url}...")
    # Commented out to reduce noise

    # Generate mock comments with varying intent
    comments = []

    users = [f"user_{random.randint(1, 100)}" for _ in range(limit)]

    # Templates for high/medium/low intent
    high_intent_templates = [
        "I'd happily pay $30/month for an app that focuses on actual conversation skills.",
        "Willing to invest if it means faster progress.",
        "I don't mind paying for quality. Time is money.",
    ]

    medium_intent_templates = [
        "Free apps aren't cutting it for me anymore.",
        "Considering a paid subscription to WaniKani.",
        "Looking for something more professional than Duolingo.",
    ]

    low_intent_templates = [
        "Any free alternatives?",
        "I'm broke so looking for free resources.",
        "Just use Anki, it's free.",
        "Don't pay for apps, just immerse.",
    ]

    for user in users:
        # Randomly assign intent
        rand = random.random()
        if rand > 0.85:
            text = random.choice(high_intent_templates)
        elif rand > 0.70:
            text = random.choice(medium_intent_templates)
        else:
            text = random.choice(low_intent_templates)

        comments.append({"author": f"u/{user}", "text": text, "thread_url": thread_url})

    return comments


# --- 3. Domain Logic ---
def analyze_intent(text: str) -> float:
    """
    Heuristic to score payment intent (0.0 - 1.0).
    Same logic as in the design doc.
    """
    text_lower = text.lower()

    # 0.9-1.0: Explicit willingness to pay
    if any(
        phrase in text_lower
        for phrase in ["i'd pay", "willing to pay", "happily pay", "don't mind paying"]
    ):
        return 0.95

    # 0.7-0.85: Strong dissatisfaction with free options or considering paid
    if any(
        phrase in text_lower
        for phrase in [
            "paid alternative",
            "free apps aren't",
            "invest in",
            "subscription",
            "worth it",
        ]
    ):
        return 0.80

    # <0.7: Insufficient evidence
    return 0.3


# --- 4. Nodes ---
def search_node(state: AgentState):
    """
    Searches subreddits for threads.
    """
    print(f"\n--- Step: Searching (Iteration {state['iteration']}) ---")

    query = state["query"]
    subreddits = state["target_subreddits"]

    all_threads = []

    # In a real scenario, we might rotate subreddits or check all.
    # For this mock, we just check them all.
    for sub in subreddits:
        threads = mock_search_reddit(query, sub, limit=3)
        all_threads.extend(threads)

    print(f"Found {len(all_threads)} potential threads.")

    return {"threads_to_process": all_threads, "iteration": state["iteration"] + 1}


def analyze_node(state: AgentState):
    """
    Fetches comments for threads and identifies candidates.
    """
    print("--- Step: Analyzing Threads & Comments ---")

    threads = state["threads_to_process"]
    visited = set(state["visited_threads"])
    current_candidates = list(state["candidates"])
    min_score = state["min_intent_score"]

    new_candidates_count = 0

    for thread in threads:
        url = thread["url"]
        if url in visited:
            continue

        visited.add(url)

        # Fetch comments
        comments = mock_get_thread_comments(url, limit=5)

        for comment in comments:
            score = analyze_intent(comment["text"])

            if score >= min_score:
                # Check if user already exists in our list (deduplication)
                if any(c["username"] == comment["author"] for c in current_candidates):
                    continue

                candidate = {
                    "username": comment["author"],
                    "intent_score": score,
                    "subreddit": thread["subreddit"],
                    "thread_title": thread["title"],
                    "evidence": comment["text"],
                    "thread_url": url,
                }
                current_candidates.append(candidate)
                new_candidates_count += 1

                # Print status within the node if needed or rely on final report
                # print(f"  + New Candidate: {candidate['username']} (Score: {score})")

    print(f"Analysis complete. Found {new_candidates_count} new candidates this batch.")

    return {
        "visited_threads": list(visited),
        "candidates": current_candidates,
        "threads_to_process": [],  # Clear processed threads
    }


def check_conditions_node(state: AgentState):
    """
    Checks if we have met the goal or hit limits.
    """
    num_candidates = len(state["candidates"])
    max_users = state["max_users"]

    print(f"Total candidates so far: {num_candidates}/{max_users}")

    is_complete = False
    if num_candidates >= max_users:
        print(f"Goal met: Found {num_candidates} candidates.")
        is_complete = True
    elif state["iteration"] > 5:  # Hard max iterations for safety
        print("Max iterations reached.")
        is_complete = True

    return {"is_complete": is_complete}


def should_continue(state: AgentState):
    """
    Conditional logic to determine next step.
    """
    if state["is_complete"]:
        return "end"
    return "continue"


# --- 5. Graph Construction ---
def build_graph():
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("search", search_node)
    workflow.add_node("analyze", analyze_node)
    workflow.add_node("check_conditions", check_conditions_node)

    # Set entry point
    workflow.set_entry_point("search")

    # Add edges
    workflow.add_edge("search", "analyze")
    workflow.add_edge("analyze", "check_conditions")

    # Conditional edges
    workflow.add_conditional_edges(
        "check_conditions", should_continue, {"continue": "search", "end": END}
    )

    return workflow.compile()


# --- 6. Main Execution ---
if __name__ == "__main__":
    print("Initializing Reddit Scout Agent (LangGraph)...")

    try:
        app = build_graph()

        initial_state = {
            "query": "japanese learning app",
            "target_subreddits": ["LearnJapanese", "languagelearning", "Japanese"],
            "max_users": 20,  # Low number for quick demo
            "min_intent_score": 0.7,
            "visited_threads": [],
            "candidates": [],
            "threads_to_process": [],
            "iteration": 1,
            "is_complete": False,
        }

        print(f"Starting search for {initial_state['max_users']} candidates...")

        # Invoke the graph
        final_output = app.invoke(initial_state)

        print("\n" + "=" * 50)
        print("FINAL RESULTS")
        print("=" * 50)

        candidates = final_output["candidates"]
        print(f"Total Candidates Found: {len(candidates)}")

        for i, c in enumerate(candidates, 1):
            print(f"\n{i}. {c['username']} (Score: {c['intent_score']})")
            print(f"   Subreddit: r/{c['subreddit']}")
            print(f'   Evidence: "{c["evidence"]}"')

        print("\nExecution Complete.")

    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback

        traceback.print_exc()
