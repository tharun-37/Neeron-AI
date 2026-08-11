import logging
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger("NeeronAi")

class PersistentMemoryDB:
    """Persistent vector & document memory manager using ChromaDB for long-term user preferences, facts, and conversation context."""
    def __init__(self, db_dir: Optional[Path] = None):
        self.db_dir = Path(db_dir) if db_dir else Path(tempfile.gettempdir()) / "neeron_memory_db"
        self.db_dir.mkdir(parents=True, exist_ok=True)
        self.client = None
        self.collection = None
        self._init_db()
    
    def _init_db(self):
        try:
            import chromadb
            self.client = chromadb.PersistentClient(path=str(self.db_dir))
            self.collection = self.client.get_or_create_collection(name="neeron_longterm_memory")
            logger.info(f"ChromaDB persistent memory initialized at {self.db_dir}")
        except Exception as e:
            logger.warning(f"ChromaDB initialization failed: {e}")
    
    def store_memory(self, memory_id: str, text: str, metadata: Optional[Dict[str, Any]] = None):
        """Stores a fact, user preference, or key instruction permanently in vector memory."""
        if not self.collection:
            return "ChromaDB memory store unavailable."
        
        try:
            self.collection.upsert(
                documents=[text],
                ids=[memory_id],
                metadatas=[metadata or {"type": "general_user_fact"}]
            )
            logger.info(f"Stored permanent memory [{memory_id}]: {text[:40]}...")
            return f"Memory stored successfully: '{text[:50]}...'"
        except Exception as e:
            logger.error(f"Error storing memory in ChromaDB: {e}")
            return f"Error storing memory: {e}"
    
    def query_memory(self, query_text: str, n_results: int = 3) -> str:
        """Queries vector memory for relevant facts, habits, or past preferences matching the prompt."""
        if not self.collection:
            return "ChromaDB memory store unavailable."
        
        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results
            )
            documents = results.get("documents", [[]])[0]
            if documents:
                memory_str = "\n".join([f"• {doc}" for doc in documents if doc])
                return f"Relevant Stored Memory Facts:\n{memory_str}"
            return "No relevant past memory found."
        except Exception as e:
            logger.error(f"Error querying memory in ChromaDB: {e}")
            return "No relevant past memory found."
