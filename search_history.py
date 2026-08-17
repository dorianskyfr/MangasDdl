import json
from pathlib import Path
from typing import List
from collections import OrderedDict

HISTORY_FILE = Path("search_history.json")
MAX_HISTORY = 30

class SearchHistoryManager:
    def __init__(self):
        self.history: List[str] = []
        self.load()
    
    def load(self):
        if HISTORY_FILE.exists():
            try:
                with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                    self.history = json.load(f)
            except Exception:
                self.history = []
    
    def save(self):
        try:
            with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    
    def add(self, query: str):
        query = query.strip()
        if not query:
            return
        # Remove if already exists to move to top
        if query in self.history:
            self.history.remove(query)
        self.history.insert(0, query)
        # Trim to max size
        self.history = self.history[:MAX_HISTORY]
        self.save()
    
    def get_suggestions(self, prefix: str = '') -> List[str]:
        prefix = prefix.strip().lower()
        if not prefix:
            return self.history[:10]
        return [h for h in self.history if prefix in h.lower()][:10]
    
    def clear(self):
        self.history = []
        self.save()

search_history = SearchHistoryManager()
