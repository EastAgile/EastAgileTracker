# linear/models.py

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class LinearUser:
    id: str
    name: str
    email: str


@dataclass
class LinearTeam:
    id: str
    name: str
    key: str
    description: Optional[str] = None


@dataclass
class LinearProject:
    id: str
    name: str
    team_id: str
    description: Optional[str] = None


@dataclass
class LinearCycle:
    id: str
    number: int
    name: str
    start_date: datetime
    end_date: datetime
    team_id: str


@dataclass
class LinearWorkflowState:
    id: str
    name: str
    type: str  # 'backlog', 'unstarted', 'started', 'completed', 'canceled'


@dataclass
class LinearLabel:
    id: str
    name: str
    team_id: str


@dataclass
class LinearComment:
    id: str
    body: str
    user_id: str
    created_at: datetime
    issue_id: str


@dataclass
class LinearAttachment:
    id: str
    title: str
    url: str
    issue_id: str


@dataclass
class LinearIssue:
    id: str
    title: str
    team_id: str
    creator_id: str
    state_id: str
    description: Optional[str] = None
    project_id: Optional[str] = None
    cycle_id: Optional[str] = None
    assignee_id: Optional[str] = None
    priority: int = 0
    estimate: Optional[float] = None
    labels: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    parent_id: Optional[str] = None
    sub_issues: List["LinearIssue"] = field(default_factory=list)
    comments: List[LinearComment] = field(default_factory=list)
    attachments: List[LinearAttachment] = field(default_factory=list)


@dataclass
class LinearIssueRelation:
    id: str
    issue_id: str
    related_issue_id: str
    type: str  # 'blocks', 'blocked_by', 'relates_to', etc.
