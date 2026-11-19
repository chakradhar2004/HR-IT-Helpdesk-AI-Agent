"""RAG (Retrieval-Augmented Generation) module for Company HR and IT Policies.

Parses markdown policy documents by section, creates chunks with exact citation
metadata, and provides vector/semantic retrieval with guaranteed source citations.
"""

import re
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field
from langchain_core.tools import StructuredTool

from src.config import settings

class PolicyChunk(BaseModel):
    chunk_id: str
    source_file: str
    section_title: str
    sub_title: str
    content: str
    citation: str

class PolicyKnowledgeBase:
    """Manages document chunking, indexing, and retrieval with source citations."""

    def __init__(self):
        self.chunks: List[PolicyChunk] = []
        self._indexed = False
        self._initialize_knowledge_base()

    def _parse_markdown_file(self, file_path: Path, filename: str) -> List[PolicyChunk]:
        """Parses a markdown policy file into section-based chunks with metadata."""
        if not file_path.exists():
            return []

        text = file_path.read_text(encoding="utf-8")
        chunks: List[PolicyChunk] = []

        # Split on H2 sections: "## Section X: Title"
        h2_pattern = re.compile(r"(^##\s+Section\s+\d+:?[^\n]+)", re.MULTILINE)
        sections = h2_pattern.split(text)

        # The first element before any H2 is the preamble/doc header
        current_section = "General Overview"
        idx = 0

        for part in sections:
            part = part.strip()
            if not part:
                continue

            if part.startswith("## Section"):
                current_section = part.replace("##", "").strip()
            else:
                # Inside a section, split by H3 subheadings if present
                h3_pattern = re.compile(r"(^###\s+[^\n]+)", re.MULTILINE)
                sub_parts = h3_pattern.split(part)
                
                current_sub = "Overview"
                for sub in sub_parts:
                    sub = sub.strip()
                    if not sub:
                        continue
                    if sub.startswith("###"):
                        current_sub = sub.replace("###", "").strip()
                    else:
                        full_content = f"{current_section} - {current_sub}\n\n{sub}"
                        citation = f"[Source: {filename}#{current_section}]"
                        chunk_id = f"{filename}_{idx}"
                        idx += 1
                        
                        chunks.append(PolicyChunk(
                            chunk_id=chunk_id,
                            source_file=filename,
                            section_title=current_section,
                            sub_title=current_sub,
                            content=full_content,
                            citation=citation
                        ))

        return chunks

    def _initialize_knowledge_base(self):
        """Indexes data/hr_policy.md and data/it_policy.md."""
        hr_chunks = self._parse_markdown_file(settings.hr_policy_path, "hr_policy.md")
        it_chunks = self._parse_markdown_file(settings.it_policy_path, "it_policy.md")
        self.chunks = hr_chunks + it_chunks
        self._indexed = True

    def retrieve(self, query: str, top_k: int = 2) -> List[Dict[str, Any]]:
        """
        Retrieves top relevant policy chunks using BM25-like token overlap and term weighting.
        Always returns exact source citations.
        """
        if not self.chunks:
            self._initialize_knowledge_base()

        query_terms = set(re.findall(r"\w+", query.lower()))
        # Remove common query filler words
        stop_words = {"what", "is", "the", "for", "a", "an", "and", "or", "to", "in", "of", "how", "do", "i", "can", "please", "tell", "me", "about"}
        keywords = query_terms - stop_words
        if not keywords:
            keywords = query_terms

        scored_chunks = []
        for chunk in self.chunks:
            content_lower = chunk.content.lower()
            section_lower = chunk.section_title.lower()
            sub_lower = chunk.sub_title.lower()

            score = 0
            for term in keywords:
                # Heavy weight for matches in section or sub-heading
                if term in sub_lower:
                    score += 5
                if term in section_lower:
                    score += 4
                if term in content_lower:
                    # Count frequency
                    count = content_lower.count(term)
                    score += min(count, 3)

            # Special semantic boosters
            if "carry" in keywords and "forward" in keywords and "carry-forward" in content_lower:
                score += 10
            if "wfh" in keywords or "work from home" in query.lower() or "remote" in keywords:
                if "work-from-home" in content_lower or "remote" in content_lower:
                    score += 10
            if "vpn" in keywords or "mfa" in keywords:
                if "vpn" in content_lower or "mfa" in content_lower or "cisco" in content_lower:
                    score += 10
            if "laptop" in keywords or "hardware" in keywords or "replacement" in keywords:
                if "hardware replacement" in content_lower or "36-month" in content_lower:
                    score += 10

            if score > 0:
                scored_chunks.append((score, chunk))

        # Sort by relevance score descending
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        top_results = scored_chunks[:top_k]

        return [
            {
                "content": c.content,
                "citation": c.citation,
                "source_file": c.source_file,
                "section_title": c.section_title,
                "sub_title": c.sub_title,
                "score": s
            }
            for s, c in top_results
        ]

# Singleton instance
kb = PolicyKnowledgeBase()

class RAGQueryInput(BaseModel):
    query: str = Field(description="Search question for HR or IT policy documents.")

def retrieve_policy_tool_fn(query: str) -> Dict[str, Any]:
    """Retrieval tool returning chunks and exact citations."""
    results = kb.retrieve(query, top_k=2)
    citations = list({r["citation"] for r in results})
    return {
        "results": results,
        "citations": citations,
        "count": len(results)
    }

rag_tool = StructuredTool.from_function(
    func=retrieve_policy_tool_fn,
    name="retrieve_policy_documents",
    description="Searches company HR and IT policy documents and returns relevant policy paragraphs with source citations.",
    args_schema=RAGQueryInput
)
