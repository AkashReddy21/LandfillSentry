from dataclasses import dataclass
from typing import Dict

from ..schemas import Candidate, EvidencePanel, Site


@dataclass
class PromptBundle:
    prompt_contract_version: str
    output_schema_version: str
    system_prompt: str
    user_prompt: str
    metadata_block: str

    def as_dict(self) -> Dict:
        return {
            "prompt_contract_version": self.prompt_contract_version,
            "output_schema_version": self.output_schema_version,
            "system_prompt": self.system_prompt,
            "user_prompt": self.user_prompt,
            "metadata_block": self.metadata_block,
        }


class PromptContractService:
    PROMPT_CONTRACT_VERSION = "phase4.prompt.v1"
    OUTPUT_SCHEMA_VERSION = "phase4.incident.v1"

    def build_prompt_bundle(self, site: Site, panel: EvidencePanel, candidate: Candidate) -> PromptBundle:
        metadata_block = (
            panel.metadata_json.get("metadata_text")
            or (
                f"site_id={site.site_id}; candidate_id={candidate.candidate_id}; "
                f"score={candidate.candidate_score:.2f}; recurrence={candidate.temporal_recurrence:.2f}; "
                f"zone_prior={candidate.likely_source_zone_prior.value}"
            )
        )
        system_prompt = (
            "You are LandfillSentry Incident Assistant. Return JSON only. "
            "Do not include markdown or narrative. Use enum values exactly as specified."
        )
        user_prompt = (
            "Interpret the evidence panel and produce an incident object using this schema: "
            "{incident_id, site_id, job_id, analysis_time, plume_likely, confidence, bbox_norm, "
            "likely_source_zone, persistence_score, priority_tier, severity_tier, review_status, "
            "feedback_status, evidence_summary, recommended_followup, model_version}. "
            f"Metadata: {metadata_block}."
        )
        return PromptBundle(
            prompt_contract_version=self.PROMPT_CONTRACT_VERSION,
            output_schema_version=self.OUTPUT_SCHEMA_VERSION,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            metadata_block=metadata_block,
        )
