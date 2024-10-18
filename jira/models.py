from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class JiraUser:
    email: str
    display_name: str
    account_id: Optional[str] = None
    active: bool = False


@dataclass
class JiraProject:
    key: str
    name: str
    description: Optional[str] = None
    lead: Optional[JiraUser] = None
    url: Optional[str] = None


@dataclass
class JiraIssueType:
    name: str
    description: Optional[str] = None


@dataclass
class JiraStatus:
    name: str
    description: Optional[str] = None


@dataclass
class JiraPriority:
    id: int
    name: str


@dataclass
class JiraComment:
    id: str
    body: str
    author: JiraUser
    created: datetime
    updated: Optional[datetime] = None


@dataclass
class JiraAttachment:
    filename: str
    size: int


@dataclass
class JiraSubTask:
    key: str
    summary: str
    parent_key: str
    description: Optional[str] = None
    assignee: Optional[JiraUser] = None
    status: Optional[str] = None
    created: Optional[datetime] = None
    updated: Optional[datetime] = None


@dataclass
class JiraIssue:
    project: JiraProject
    key: str
    summary: str
    issue_type: JiraIssueType
    description: Optional[str] = None
    assignee: Optional[JiraUser] = None
    reporter: Optional[JiraUser] = None
    priority: Optional[JiraPriority] = None
    status: Optional[JiraStatus] = None
    labels: List[str] = field(default_factory=list)
    comments: List[JiraComment] = field(default_factory=list)
    attachments: List[JiraAttachment] = field(default_factory=list)
    epic: Optional["JiraEpic"] = None
    parent: Optional["JiraIssue"] = None
    subtasks: List[JiraSubTask] = field(default_factory=list)
    created: Optional[datetime] = None
    updated: Optional[datetime] = None


@dataclass
class JiraEpic(JiraIssue):
    issues: List[JiraIssue] = field(default_factory=list)


@dataclass
class JiraStory(JiraIssue):
    points: Optional[float] = None


@dataclass
class JiraSprint:
    id: int
    name: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    board_id: int = None


@dataclass
class JiraBlocker:
    blocker: JiraIssue
    blocked: JiraIssue
    description: Optional[str] = None
