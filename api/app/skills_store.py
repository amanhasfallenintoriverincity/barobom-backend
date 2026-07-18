"""Skill store backed by ChromaDB — vector search for device skills."""
import os
import re
import yaml
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions

_BASE = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SKILLS_DIR = _BASE / "skills"
CHROMA_PATH = _BASE / ".chromadb"
COLLECTION_NAME = "device_skills"

# Lightweight local embedding model
_ef = embedding_functions.DefaultEmbeddingFunction()

_client = None
_collection = None


def _get_collection():
    global _client, _collection
    if _collection is not None:
        return _collection
    _client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    _collection = _client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=_ef,
        metadata={"hnsw:space": "cosine"},
    )
    return _collection


def parse_skill_md(path: Path) -> dict | None:
    """Parse a SKILL.md file with YAML frontmatter."""
    text = path.read_text(encoding="utf-8")
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", text, re.DOTALL)
    if not match:
        return None
    try:
        meta = yaml.safe_load(match.group(1))
        body = match.group(2).strip()
    except yaml.YAMLError:
        return None

    device = meta.get("device", {})
    return {
        "id": str(path.relative_to(SKILLS_DIR)).replace("/", "-").replace(".md", ""),
        "device_name": device.get("name", ""),
        "category": device.get("category", ""),
        "brand": device.get("brand", ""),
        "model": device.get("model", ""),
        "status": meta.get("status", "published"),
        "version": meta.get("version", "1.0.0"),
        "content": body,
        "search_text": f"{device.get('name', '')} {device.get('brand', '')} {device.get('model', '')} {body[:500]}",
    }


def load_all_skills():
    """Scan skills/ directory and upsert into ChromaDB."""
    collection = _get_collection()
    docs = []
    metadatas = []
    ids = []

    for md_path in sorted(SKILLS_DIR.rglob("*.md")):
        if md_path.name == "README.md":
            continue
        parsed = parse_skill_md(md_path)
        if parsed is None or parsed["status"] != "published":
            continue
        docs.append(parsed["search_text"])
        metadatas.append({
            "device_name": parsed["device_name"],
            "category": parsed["category"],
            "brand": parsed["brand"],
            "model": parsed["model"],
            "version": parsed["version"],
            "content": parsed["content"],
        })
        ids.append(parsed["id"])

    if not docs:
        print("[skills] No skills found to load")
        return

    existing = collection.get()["ids"]
    if existing:
        collection.delete(ids=existing)

    collection.add(documents=docs, metadatas=metadatas, ids=ids)
    print(f"[skills] Loaded {len(ids)} skills into ChromaDB")


def search_skills(query: str, n_results: int = 3) -> list[dict]:
    """Search skills by text query using vector similarity."""
    collection = _get_collection()
    if collection.count() == 0:
        return []

    results = collection.query(query_texts=[query], n_results=n_results)
    out = []
    if not results["ids"] or not results["ids"][0]:
        return out

    for i, doc_id in enumerate(results["ids"][0]):
        meta = results["metadatas"][0][i] if results["metadatas"] else {}
        dist = results["distances"][0][i] if results["distances"] else 0.0
        out.append({
            "id": doc_id,
            "title": (meta.get("device_name", "") or doc_id),
            "content": meta.get("content", ""),
            "category": meta.get("category", ""),
            "brand": meta.get("brand", ""),
            "model": meta.get("model", ""),
            "version": meta.get("version", "1.0.0"),
            "score": round(1.0 - dist, 4) if dist else 0.0,
        })
    return out


def search_by_device(brand: str, model: str, category: str = "", n_results: int = 3) -> list[dict]:
    """Search skills matching a specific device."""
    query_parts = [brand, model]
    if category:
        query_parts.append(category)
    query = " ".join(query_parts)
    return search_skills(query, n_results=n_results)
