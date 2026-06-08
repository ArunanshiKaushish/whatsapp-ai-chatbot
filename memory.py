"""Long-term memory extraction, storage, and semantic keyword retrieval."""

import json
import logging
import re
from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Memory, utcnow

logger = logging.getLogger(__name__)

# Common stop words for keyword scoring
STOP_WORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "must", "shall", "can", "need", "dare",
    "ought", "used", "to", "of", "in", "for", "on", "with", "at", "by",
    "from", "as", "into", "through", "during", "before", "after", "above",
    "below", "between", "under", "again", "further", "then", "once", "here",
    "there", "when", "where", "why", "how", "all", "each", "few", "more",
    "most", "other", "some", "such", "no", "nor", "not", "only", "own",
    "same", "so", "than", "too", "very", "just", "and", "but", "if", "or",
    "because", "until", "while", "although", "though", "after", "before",
    "what", "which", "who", "whom", "this", "that", "these", "those", "am",
    "i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you",
    "your", "yours", "yourself", "yourselves", "he", "him", "his", "himself",
    "she", "her", "hers", "herself", "it", "its", "itself", "they", "them",
    "their", "theirs", "themselves", "about", "up", "out", "off", "over",
    "under", "again", "tell", "know", "please", "thanks", "thank", "hi",
    "hello", "hey", "yes", "no", "ok", "okay",
}


def _tokenize(text: str) -> set[str]:
    """Extract meaningful keywords from text."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {w for w in words if len(w) > 2 and w not in STOP_WORDS}


def _score_memory(query_tokens: set[str], memory_text: str) -> float:
    """Score a memory by keyword overlap with the query."""
    if not query_tokens:
        return 0.0
    memory_tokens = _tokenize(memory_text)
    if not memory_tokens:
        return 0.0
    overlap = query_tokens & memory_tokens
    if not overlap:
        return 0.0
    # Weight by overlap ratio and absolute match count
    return len(overlap) / len(query_tokens) + (len(overlap) * 0.1)


def save_memory(session: Session, user_id: int, memory_text: str) -> Memory:
    """Save a new long-term memory for a user."""
    memory_text = memory_text.strip()
    if not memory_text:
        raise ValueError("memory_text cannot be empty")

    memory = Memory(user_id=user_id, memory_text=memory_text)
    session.add(memory)
    session.flush()
    logger.info("Saved memory for user_id=%s: %s", user_id, memory_text[:80])
    return memory


def update_memory(session: Session, memory_id: int, memory_text: str) -> Memory | None:
    """Update an existing memory's text."""
    memory = session.get(Memory, memory_id)
    if memory is None:
        return None
    memory.memory_text = memory_text.strip()
    memory.updated_at = utcnow()
    session.flush()
    logger.info("Updated memory id=%s: %s", memory_id, memory_text[:80])
    return memory


def retrieve_relevant_memories(
    session: Session,
    user_id: int,
    query: str,
    limit: int = 10,
) -> list[Memory]:
    """
    Retrieve memories relevant to the current query using semantic keyword matching.

    Falls back to most recent memories when no keyword matches are found.
    """
    all_memories = session.scalars(
        select(Memory).where(Memory.user_id == user_id).order_by(Memory.updated_at.desc())
    ).all()

    if not all_memories:
        return []

    query_tokens = _tokenize(query)
    if not query_tokens:
        return list(all_memories[:limit])

    scored = [
        (memory, _score_memory(query_tokens, memory.memory_text))
        for memory in all_memories
    ]
    scored.sort(key=lambda item: item[1], reverse=True)

    relevant = [m for m, score in scored if score > 0]
    if relevant:
        logger.debug(
            "Retrieved %d relevant memories for user_id=%s", len(relevant[:limit]), user_id
        )
        return relevant[:limit]

    # No keyword matches — return most recent memories for general context
    logger.debug(
        "No keyword matches; returning %d recent memories for user_id=%s",
        min(limit, len(all_memories)),
        user_id,
    )
    return list(all_memories[:limit])


def _find_similar_memory(
    session: Session, user_id: int, memory_text: str
) -> Memory | None:
    """Find an existing memory with high keyword overlap (for deduplication/updates)."""
    new_tokens = _tokenize(memory_text)
    if not new_tokens:
        return None

    memories = session.scalars(select(Memory).where(Memory.user_id == user_id)).all()
    best_match: Memory | None = None
    best_score = 0.0

    for memory in memories:
        score = _score_memory(new_tokens, memory.memory_text)
        if score > best_score and score >= 0.5:
            best_score = score
            best_match = memory

    return best_match


def extract_and_store_memories(
    session: Session,
    user_id: int,
    user_message: str,
    assistant_reply: str,
    claude_extract_fn,
) -> list[Memory]:
    """
    Use Claude to extract durable facts from the exchange and persist them.

    claude_extract_fn: callable(user_message, assistant_reply) -> list[str]
    """
    try:
        facts = claude_extract_fn(user_message, assistant_reply)
    except Exception:
        logger.exception("Memory extraction failed for user_id=%s", user_id)
        return []

    stored: list[Memory] = []
    for fact in facts:
        fact = fact.strip()
        if not fact or len(fact) < 3:
            continue

        existing = _find_similar_memory(session, user_id, fact)
        if existing:
            # Update if the new fact is more detailed
            if len(fact) > len(existing.memory_text):
                update_memory(session, existing.id, fact)
                stored.append(existing)
        else:
            stored.append(save_memory(session, user_id, fact))

    if stored:
        logger.info("Stored/updated %d memories for user_id=%s", len(stored), user_id)
    return stored


def parse_memory_extraction_response(raw: str) -> list[str]:
    """Parse Claude's JSON array of memory strings."""
    raw = raw.strip()
    if not raw:
        return []

    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [str(item).strip() for item in data if str(item).strip()]
    except json.JSONDecodeError:
        pass

    # Fallback: one fact per line
    return [line.strip("- ").strip() for line in raw.splitlines() if line.strip()]
