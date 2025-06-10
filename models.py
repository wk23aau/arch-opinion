# models.py
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
from pathlib import Path

@dataclass
class ProjectInfo:
    address: str
    project_type: str
    council: Optional[str] = None
    planning_reference: Optional[str] = None
    
@dataclass
class UploadedDocument:
    file_path: Path
    document_type: str
    file_uri: Optional[str] = None  # Google File API URI
    
@dataclass
class AnalysisRequest:
    project_info: ProjectInfo
    documents: List[UploadedDocument]
    selected_frameworks: List[str]
    user_prompt: str
    created_at: datetime = field(default_factory=datetime.now)
    
@dataclass
class AnalysisReport:
    ai_review_framework: List[Dict]
    plan_by_plan_review: List[Dict]
    policy_compatibility_summary: List[Dict]
    ai_recommendation_summary: str