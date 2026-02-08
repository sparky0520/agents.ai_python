import os
import sys
import importlib.util
import shutil
import tempfile
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = "test"  # Default for now, ideally from env


class AgentLoader:
    def __init__(self):
        self._mongo_client = None
        self._db = None
        # Cache agents in a temporary directory
        self._base_cache_dir = os.path.join(tempfile.gettempdir(), "agents_cache")
        os.makedirs(self._base_cache_dir, exist_ok=True)
        print(
            f"DEBUG: AgentLoader initialized. Cache dir: {self._base_cache_dir} | File: {__file__}"
        )

    @property
    def db(self):
        if self._db is None:
            if not MONGODB_URI:
                raise ValueError("MONGODB_URI not set")
            self._mongo_client = MongoClient(MONGODB_URI)
            self._db = self._mongo_client[DB_NAME]
        return self._db

    def get_agent_module(self, agent_id: str):
        """
        Fetches agent files from MongoDB, saves them to cache, and imports the module.
        Returns the module object.
        """
        agent_dir = os.path.join(self._base_cache_dir, agent_id)

        # Fetch from DB
        self._fetch_and_save_agent(agent_id, agent_dir)

        # 2. Dynamically import the module
        agent_yaml_path = os.path.join(agent_dir, "agent.yaml")
        if not os.path.exists(agent_yaml_path):
            # Fallback: maybe just look for .py if no yaml
            pass

        # Let's look for the first .py file that is not standard.
        py_files = [
            f for f in os.listdir(agent_dir) if f.endswith(".py") and f != "__init__.py"
        ]
        if not py_files:
            raise FileNotFoundError(f"No python script found for agent {agent_id}")

        script_name = py_files[0]  # Take the first one for now
        script_path = os.path.join(agent_dir, script_name)

        # Use a unique module name to avoid conflicts
        module_name = f"agents_cache.{agent_id}.{script_name[:-3]}"

        # Add cache dir to sys.path if not there
        if self._base_cache_dir not in sys.path:
            sys.path.append(self._base_cache_dir)

        # Import
        spec = importlib.util.spec_from_file_location(module_name, script_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load spec for {script_path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        return module

    def _fetch_and_save_agent(self, agent_id: str, dest_dir: str):
        print(f"Fetching agent {agent_id} from MongoDB...")
        try:
            agent_doc = self.db.agents.find_one({"agent_id": agent_id})
        except Exception as e:
            print(f"DB Error: {e}")
            agent_doc = None

        if not agent_doc:
            # If not in DB, maybe we can't do anything
            # But if we are testing, let's check if the directory already exists in cache (maybe manually placed)
            if os.path.exists(dest_dir):
                print(f"Agent {agent_id} found in cache, using cached version.")
                return
            raise ValueError(
                f"Agent {agent_id} not found in database or local dev paths"
            )

        if os.path.exists(dest_dir):
            shutil.rmtree(dest_dir)
        os.makedirs(dest_dir)

        files = agent_doc.get("files", [])
        for file_data in files:
            file_path = os.path.join(dest_dir, file_data["name"])
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(file_data["content"])

        print(f"Agent {agent_id} saved to {dest_dir}")


# Global loader instance
loader = AgentLoader()
