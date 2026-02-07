from typing import TypedDict, List, Dict
from langgraph.graph import StateGraph, END
import time
import os
import praw
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize PRAW
reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent=os.getenv(
        "REDDIT_USER_AGENT", "python:agents-ai-python:v0.1.0 (by /u/developer)"
    ),
)


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


# --- 2. Tools (Real PRAW Implementation) ---
def search_reddit(query: str, subreddit: str, limit: int = 5) -> List[Dict]:
    """
    Searches Reddit for threads using PRAW.
    Returns a list of thread objects.
    """
    print(f"  [Tool] Searching r/{subreddit} for '{query}'...")

    threads = []
    try:
        # Search typically returns a generator
        search_results = reddit.subreddit(subreddit).search(query, limit=limit)

        for submission in search_results:
            threads.append(
                {
                    "id": submission.id,
                    "url": f"https://reddit.com{submission.permalink}",
                    "title": submission.title,
                    "subreddit": subreddit,
                    "submission_obj": submission,  # Keep reference for comment fetching if needed, though we strictly use URL/ID usually
                }
            )
    except Exception as e:
        print(f"  [Error] Failed to search r/{subreddit}: {e}")

    return threads


def get_thread_comments(thread_id: str, limit: int = 10) -> List[Dict]:
    """
    Fetches comments for a thread using PRAW.
    Returns a list of comment objects.
    """
    # print(f"  [Tool] Fetching comments for thread {thread_id}...")

    comments = []
    try:
        submission = reddit.submission(id=thread_id)

        # This triggers a network request to fetch comments
        submission.comments.replace_more(
            limit=0
        )  # Flatten comment tree, remove "load more"

        # Just get top-level comments or flat list depending on depth requirements.
        # For simplicity, let's look at top-level comments.
        # To get all, uses submission.comments.list()

        count = 0
        for comment in submission.comments.list():
            if count >= limit:
                break

            if isinstance(comment, praw.models.Comment) and comment.author:
                comments.append(
                    {
                        "author": comment.author.name,
                        "text": comment.body,
                        "thread_url": submission.permalink,
                    }
                )
                count += 1

    except Exception as e:
        print(f"  [Error] Failed to fetch comments for {thread_id}: {e}")

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
    # For this implementation, we just check them all.
    for sub in subreddits:
        try:
            threads = search_reddit(query, sub, limit=3)
            all_threads.extend(threads)
            # Be nice to API
            time.sleep(1.0)
        except Exception as e:
            print(f"Error searching {sub}: {e}")

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
        thread_id = thread["id"]
        url = thread["url"]

        if url in visited:
            continue

        visited.add(url)

        # Fetch comments
        comments = get_thread_comments(thread_id, limit=20)

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

                print(f"  + New Candidate: {candidate['username']} (Score: {score})")

        # Rate limiting
        time.sleep(0.5)

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
    elif (
        state["iteration"] > 3
    ):  # Hard max iterations for safety (reduced for real API)
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
    print("Initializing Reddit Scout Agent (PRAW + LangGraph)...")

    # Check for credentials
    if not os.getenv("REDDIT_CLIENT_ID") or not os.getenv("REDDIT_CLIENT_SECRET"):
        print("\n[ERROR] Reddit API credentials not found.")
        print(
            "Please create a .env file with REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET."
        )
        print("See .env.example for details.\n")
        exit(1)

    try:
        app = build_graph()

        initial_state = {
            "query": "japanese learning app",
            "target_subreddits": ["LearnJapanese", "languagelearning", "Japanese"],
            "max_users": 5,  # Low number for demo
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
            print(f'   Evidence: "{c["evidence"][:150]}..."')  # Truncate evidence

        print("\nExecution Complete.")

    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback

        traceback.print_exc()
