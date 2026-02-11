"""Fact checker for verifying claims against web and local sources.

Features:
- Decompose claims into atomic facts using LLM
- Verify facts against Linkup web search
- Cross-reference with local documents
- Generate verification reports with confidence scores
- Suggest calendar events for deadlines
- Support for various claim types (funding, revenue, dates, etc.)

Usage:
    checker = FactChecker()

    # Verify a claim
    result = await checker.verify_claim(
        claim="Acme raised $50M Series B",
        sources=[{"content": "...", "source": "local_doc"}]
    )

    # Full verification report
    report = await checker.verify_report(
        user_claim="What funding has Acme raised?",
        linkup_results=linkup_search,
        local_docs=[...]
    )
"""

import json
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from app.services.llm import create_llm_client
from app.services.linkup import create_linkup_client
from app.utils.ics_utils import ICSUtils
from app.services.content_store import ContentStore, create_content_store
from app.models.content_item import ContentItem, SourceType


class FactClaim(BaseModel):
    """Model for individual fact verification."""

    claim: str
    is_verified: bool
    confidence: float
    sources: List[str]
    evidence_summary: str
    verdict: str  # "SUPPORTED" | "CONTRADICTED" | "UNVERIFIED"


class VerificationReport(BaseModel):
    """Model for full verification report."""

    original_claim: str
    overall_verdict: str  # "SUPPORTED" | "CONTRADICTED" | "UNVERIFIED"
    confidence: float
    facts: List[Dict[str, Any]]
    sources_used: List[str]
    evidence_summary: str
    suggested_action: str
    has_deadline: bool
    deadline_event: Optional[Dict[str, Any]] = None


class FactChecker:
    """Verify claims against multiple sources."""

    def __init__(self):
        self.llm_client = create_llm_client()
        self.linkup_client = create_linkup_client()
        self.min_confidence_threshold = 0.6

    async def verify_claim(
        self, claim: str, sources: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Verify a claim against provided sources.

        Args:
            claim: The claim to verify
            sources: List of source dicts with 'content' and 'source' fields

        Returns:
            Dict with verification results
        """
        sources = sources or []

        # Step 1: Decompose claim into atomic facts
        facts = await self._decompose_claim(claim)

        # Step 2: Verify each fact
        verified_facts = []
        all_sources = []

        for fact in facts:
            fact_result = await self._verify_fact(fact, sources)
            verified_facts.append(fact_result)

            # Collect unique sources
            for source in fact_result.get("sources", []):
                if source not in all_sources:
                    all_sources.append(source)

        # Step 3: Assess evidence strength
        evidence_score = self._assess_evidence_strength(verified_facts)

        # Step 4: Determine overall verdict
        verdict = self._determine_overall_verdict(verified_facts)

        # Step 5: Generate evidence summary
        evidence_summary = self._generate_evidence_summary(verified_facts)

        # Step 6: Check for deadlines and suggest calendar events
        has_deadline, deadline_event = self._check_for_deadlines(claim, verified_facts)

        # Step 7: Suggest action based on verdict
        suggested_action = self._suggest_action(verdict, evidence_score)

        result = {
            "claim": claim,
            "facts": verified_facts,
            "overall_verdict": verdict,
            "confidence": round(evidence_score, 2),
            "evidence_summary": evidence_summary,
            "sources_used": all_sources,
            "suggested_action": suggested_action,
            "has_deadline": has_deadline,
            "deadline_event": deadline_event,
            "verified_at": datetime.utcnow().isoformat(),
        }

        return result

    async def _decompose_claim(self, claim: str) -> List[str]:
        """Decompose a claim into atomic facts using LLM.

        Args:
            claim: Complex claim to decompose

        Returns:
            List of atomic fact strings
        """
        prompt = f"""Decompose this claim into individual atomic facts that can be independently verified.

Claim: "{claim}"

Examples:
- "Acme raised $50M Series B in 2024" →
  - "Acme raised funding"
  - "Acme raised $50M"
  - "The round was Series B"
  - "The funding occurred in 2024"

- "Apple sold 100M iPhones last quarter" →
  - "Apple sold iPhones"
  - "Apple sold 100M units"
  - "The sales occurred last quarter"

Return ONLY a JSON array of strings. Each fact should be:
- Self-contained (can be verified alone)
- Specific (not vague)
- Verifiable (can be confirmed or denied)

JSON array:
"""

        try:
            response = self.llm_client.generate(prompt)

            # Parse JSON response
            facts = json.loads(response)

            if isinstance(facts, list):
                return [str(f).strip() for f in facts if f and str(f).strip()]
        except Exception as e:
            print(f"Error decomposing claim: {e}")

        # Fallback: return single fact
        return [claim]

    async def _verify_fact(
        self, fact: str, local_sources: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Verify a single fact against sources.

        Args:
            fact: Atomic fact to verify
            local_sources: Local document sources

        Returns:
            Dict with verification result for this fact
        """
        # Step 1: Search web via Linkup
        web_results = await self._search_web(fact)

        # Step 2: Check local documents
        local_results = self._search_local(fact, local_sources)

        # Step 3: Cross-reference findings
        cross_ref = self._cross_reference(fact, web_results, local_results)

        # Step 4: Assess evidence
        evidence = self._assess_fact_evidence(cross_ref)

        return {
            "fact": fact,
            "is_verified": evidence["supported"],
            "confidence": evidence["confidence"],
            "sources": evidence["sources"],
            "evidence_summary": evidence["summary"],
            "web_evidence": cross_ref.get("web", []),
            "local_evidence": cross_ref.get("local", []),
            "conflict": cross_ref.get("conflict", None),
        }

    async def _search_web(self, query: str) -> Dict[str, Any]:
        """Search web for fact verification using Linkup."""
        try:
            result = await self.linkup_client.search(query)
            return result
        except Exception as e:
            print(f"Linkup search error: {e}")
            return {"answer": "", "sources": []}

    def _search_local(
        self, query: str, sources: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Search local documents for fact verification."""
        if not sources:
            return []

        results = []

        for source in sources:
            content = source.get("content", "")
            source_name = source.get("source", "unknown")

            # Simple keyword matching (in production, use vector search)
            query_lower = query.lower()
            query_words = set(re.findall(r"\w+", query_lower))

            content_lower = content.lower()
            content_words = set(re.findall(r"\w+", content_lower))

            # Calculate simple overlap score
            overlap = len(query_words & content_words)

            if overlap > 0:
                # Extract relevant snippet
                for word in query_words:
                    idx = content_lower.find(word)
                    if idx >= 0:
                        start = max(0, idx - 50)
                        end = min(len(content), idx + len(word) + 50)
                        snippet = content[start:end]
                        results.append(
                            {
                                "source": source_name,
                                "relevance": overlap / len(query_words),
                                "snippet": f"...{snippet}...",
                            }
                        )
                        break

        return results

    def _cross_reference(
        self,
        fact: str,
        web_results: Dict[str, Any],
        local_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Cross-reference web and local findings."""

        conflict = None
        web_support = False
        local_support = False

        # Check web evidence
        web_answer = (
            web_results.get("answer", "").lower() if web_results.get("answer") else ""
        )
        if web_answer:
            # Check for contradictions
            negations = ["not", "never", "false", "denied", "refuted"]
            if any(neg in web_answer for neg in negations):
                # Need to check context - this is simplistic
                pass
            else:
                # Look for supporting keywords
                fact_words = fact.lower().split()
                supporting = [w for w in fact_words if len(w) > 3]
                if any(s in web_answer for s in supporting):
                    web_support = True

        # Check local evidence
        for result in local_results:
            if result.get("relevance", 0) > 0.3:
                local_support = True
                break

        # Detect conflicts
        if web_support and local_support:
            # Could implement deeper conflict detection
            pass

        return {
            "web": web_results,
            "local": local_results,
            "web_support": web_support,
            "local_support": local_support,
            "conflict": conflict,
        }

    def _assess_fact_evidence(self, cross_ref: Dict[str, Any]) -> Dict[str, Any]:
        """Assess evidence strength for a fact."""

        sources = []
        supported = False
        confidence = 0.0
        summary_parts = []

        # Web evidence
        web = cross_ref.get("web", {})
        web_sources = web.get("sources", [])
        if web_sources:
            for s in web_sources[:2]:
                sources.append(f"Web: {s.get('name', 'Unknown')}")

            web_answer = web.get("answer", "")
            if web_answer:
                summary_parts.append(f"Web search found relevant information")
                if len(web_sources) >= 2:
                    confidence += 0.4
                    supported = True

        # Local evidence
        local = cross_ref.get("local", [])
        if local:
            for result in local[:2]:
                sources.append(f"Local: {result.get('source', 'Document')}")

            summary_parts.append(f"Found local document references")
            confidence += 0.3 * len(local)
            if len(local) >= 2:
                supported = True

        # Cap confidence
        confidence = min(confidence, 1.0)

        # Generate summary
        if summary_parts:
            summary = "; ".join(summary_parts)
        else:
            summary = "No evidence found for this fact"

        return {
            "supported": supported and confidence > 0.3,
            "confidence": confidence,
            "sources": sources,
            "summary": summary,
        }

    def _assess_evidence_strength(self, facts: List[Dict[str, Any]]) -> float:
        """Assess overall evidence strength across all facts."""
        if not facts:
            return 0.0

        # Average confidence weighted by fact count
        total_confidence = sum(f.get("confidence", 0) for f in facts)
        return total_confidence / len(facts)

    def _determine_overall_verdict(self, facts: List[Dict[str, Any]]) -> str:
        """Determine overall verdict from verified facts."""
        if not facts:
            return "UNVERIFIED"

        supported_count = sum(
            1
            for f in facts
            if f.get("is_verified", False) and f.get("confidence", 0) > 0.5
        )
        contradicted_count = sum(
            1
            for f in facts
            if not f.get("is_verified", True) and f.get("confidence", 0) > 0.5
        )

        total_checked = supported_count + contradicted_count

        if total_checked == 0:
            return "UNVERIFIED"

        ratio = supported_count / total_checked

        if ratio >= 0.7:
            return "SUPPORTED"
        elif ratio <= 0.3:
            return "CONTRADICTED"
        else:
            return "UNVERIFIED"

    def _generate_evidence_summary(self, facts: List[Dict[str, Any]]) -> str:
        """Generate human-readable evidence summary."""
        if not facts:
            return "No facts to verify"

        supported = [f for f in facts if f.get("is_verified")]
        unsupported = [f for f in facts if not f.get("is_verified")]

        summary_parts = []

        if supported:
            summary_parts.append(
                f"{len(supported)}/{len(facts)} facts verified with supporting evidence"
            )

        if unsupported:
            summary_parts.append(f"{len(unsupported)} facts could not be verified")

        return (
            "; ".join(summary_parts)
            if summary_parts
            else "Insufficient evidence for verification"
        )

    def _check_for_deadlines(self, claim: str, facts: List[Dict[str, Any]]) -> tuple:
        """Check if claim or facts contain deadlines."""

        # Check original claim for deadline keywords
        if ICSUtils.should_create_event(claim):
            # Try to extract datetime
            dt = ICSUtils.extract_datetime(claim)
            if dt:
                return True, {
                    "summary": f"Verify: {claim[:50]}...",
                    "start_time": dt.isoformat(),
                    "description": f"Fact check deadline for: {claim}",
                    "action": "Verify claim before this date",
                }

        # Check facts for deadlines
        for fact in facts:
            fact_text = fact.get("fact", "")
            if ICSUtils.should_create_event(fact_text):
                dt = ICSUtils.extract_datetime(fact_text)
                if dt:
                    return True, {
                        "summary": f"Verify fact: {fact_text[:50]}...",
                        "start_time": dt.isoformat(),
                        "description": f"Verify: {fact_text}",
                        "action": "Confirm fact accuracy",
                    }

        return False, None

    def _suggest_action(self, verdict: str, confidence: float) -> str:
        """Suggest action based on verification result."""

        if verdict == "SUPPORTED":
            if confidence > 0.8:
                return "Use freely - high confidence verified"
            else:
                return "Use with caution - partial verification"

        elif verdict == "CONTRADICTED":
            return "Do not use - claim appears false based on evidence"

        else:  # UNVERIFIED
            if confidence > 0.4:
                return "Seek additional verification sources"
            else:
                return "Treat as unverified - significant research needed"

    async def verify_report(
        self,
        user_claim: str,
        linkup_results: Dict[str, Any] = None,
        local_docs: List[Dict[str, Any]] = None,
    ) -> VerificationReport:
        """Generate full verification report.

        Args:
            user_claim: Original user claim or question
            linkup_results: Results from Linkup web search
            local_docs: Local document sources

        Returns:
            VerificationReport with full analysis
        """
        # Combine sources
        all_sources = []

        if linkup_results:
            linkup_sources = linkup_results.get("sources", [])
            for s in linkup_sources:
                all_sources.append(
                    {
                        "content": s.get("snippet", ""),
                        "source": f"Linkup: {s.get('name', 'Web')}",
                        "url": s.get("url", ""),
                    }
                )

        if local_docs:
            all_sources.extend(local_docs)

        # Verify the claim
        result = await self.verify_claim(user_claim, all_sources)

        # Build comprehensive report
        report = VerificationReport(
            original_claim=user_claim,
            overall_verdict=result["overall_verdict"],
            confidence=result["confidence"],
            facts=result["facts"],
            sources_used=result["sources_used"],
            evidence_summary=result["evidence_summary"],
            suggested_action=result["suggested_action"],
            has_deadline=result["has_deadline"],
            deadline_event=result.get("deadline_event"),
        )

        return report

    async def create_verification_ics(
        self, claim: str, verification_result: Dict[str, Any]
    ) -> Optional[str]:
        """Create ICS file for verification deadline.

        Args:
            claim: The claim being verified
            verification_result: Result from verify_claim

        Returns:
            Path to ICS file or None
        """
        if not verification_result.get("has_deadline"):
            return None

        event_data = verification_result.get("deadline_event", {})

        # Parse datetime
        dt_str = event_data.get("start_time", "")
        try:
            dt = datetime.fromisoformat(dt_str)
        except:
            dt = datetime.utcnow()

        # Create ICS
        ics_content = ICSUtils.create_event(
            summary=f"Verify: {claim[:60]}...",
            start_time=dt,
            description=f"Action: {event_data.get('action', 'Verify claim')}\n\nClaim: {claim}",
            attendees=None,
        )

        # Save file
        safe_claim = re.sub(r"[^\w\s-]", "", claim)[:40]
        filename = f"verify_{safe_claim}_{datetime.now().strftime('%Y%m%d')}.ics"

        filepath = ICSUtils.save_to_file(
            ics_content, f"./verification_deadlines/{filename}"
        )

        return filepath

    async def verify_with_store(
        self,
        claim: str,
        content_store: ContentStore,
        source_types: list[SourceType] = None,
        session_id: str = None,
    ) -> dict[str, any]:
        """Verify claim using ContentStore for local sources.

        Args:
            claim: The claim to verify
            content_store: ContentStore for querying local documents
            source_types: Optional filter for source types
            session_id: Optional session ID filter

        Returns:
            Dict with verification results plus:
                - local_sources_queried: Number of sources queried
                - content_store_queried: True
        """
        if source_types is None:
            source_types = [
                SourceType.PDF,
                SourceType.EMAIL,
                SourceType.RESEARCH,
                SourceType.NOTE,
            ]

        local_docs = []
        for st in source_types:
            items = await content_store.query_by_source(st)
            if session_id:
                items = [i for i in items if i.session_id == session_id]

            local_docs.extend(
                [
                    {
                        "content": item.content,
                        "source": f"{item.source_type.value}: {item.title}",
                        "id": item.id,
                        "metadata": item.metadata,
                    }
                    for item in items[:20]
                ]
            )

        result = await self.verify_claim(claim, local_docs)

        result["local_sources_queried"] = len(local_docs)
        result["content_store_queried"] = True

        return result

    async def verify_claims_with_store(
        self,
        claims: list[str],
        content_store: ContentStore,
        source_types: list[SourceType] = None,
        session_id: str = None,
    ) -> list[dict[str, any]]:
        """Verify multiple claims using ContentStore.

        Args:
            claims: List of claims to verify
            content_store: ContentStore for querying local documents
            source_types: Optional filter for source types
            session_id: Optional session ID filter

        Returns:
            List of verification result dicts
        """
        results = []
        for claim in claims:
            result = await self.verify_with_store(
                claim=claim,
                content_store=content_store,
                source_types=source_types,
                session_id=session_id,
            )
            results.append(result)

        return results


# Factory function
def create_fact_checker() -> FactChecker:
    """Create FactChecker instance."""
    return FactChecker()


# Testing commands
if __name__ == "__main__":
    import asyncio

    async def test():
        checker = FactChecker()

        # Test basic verification
        print("Testing fact verification...")

        result = await checker.verify_claim(
            claim="Acme Corp raised $50M Series B in February 2024",
            sources=[
                {
                    "content": "Acme Corp announced Series B funding",
                    "source": "local_note",
                },
                {"content": "TechCrunch reported $50M round", "source": "article"},
            ],
        )

        print(f"\nClaim: {result['claim']}")
        print(f"Verdict: {result['overall_verdict']}")
        print(f"Confidence: {result['confidence']}")
        print(f"Facts verified: {len(result['facts'])}")
        print(f"Evidence: {result['evidence_summary']}")
        print(f"Action: {result['suggested_action']}")
        print(f"Has deadline: {result['has_deadline']}")

        # Test deadline detection
        print("\n" + "=" * 50)

        deadline_result = await checker.verify_claim(
            claim="Submit Series B pitch deck by March 15, 2024", sources=[]
        )

        print(f"\nClaim: {deadline_result['claim']}")
        print(f"Has deadline: {deadline_result['has_deadline']}")
        if deadline_result.get("deadline_event"):
            print(f"Deadline event: {deadline_result['deadline_event']['summary']}")

    asyncio.run(test())
