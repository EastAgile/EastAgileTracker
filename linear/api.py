# linear/api.py
import asyncio
import uuid
from typing import Any, Dict, List

import aiohttp
from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport

from .config import Config
from .exceptions import LinearAPIError
from .logger import logger
from .utils import chunk_list, retry_async


class LinearAPI:
    def __init__(self):
        self.url = Config.LINEAR_API_URL
        self.token = Config.LINEAR_API_KEY
        self.client = None
        self.semaphore = asyncio.Semaphore(Config.MAX_CONCURRENT_REQUESTS)

    async def __aenter__(self):
        transport = AIOHTTPTransport(
            url=self.url, headers={"Authorization": self.token}
        )
        self.client = Client(transport=transport, fetch_schema_from_transport=True)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.client.transport.close()

    @retry_async(max_retries=3)
    async def execute_query(self, query: str, variables: Dict = None) -> Dict:
        async with self.semaphore:
            try:
                return await self.client.execute_async(
                    gql(query), variable_values=variables
                )
            except Exception as e:
                logger.error(f"API request failed: {str(e)}")
                raise LinearAPIError(f"API request failed: {str(e)}")

    async def create_team(self, name: str, key: str, description: str = None) -> Dict:
        query = """
        mutation CreateTeam($name: String!, $key: String!, $description: String) {
          teamCreate(input: {name: $name, key: $key, description: $description}) {
            success
            team {
              id
              name
              key
              description
            }
          }
        }
        """
        variables = {"name": name, "key": key, "description": description}
        result = await self.execute_query(query, variables)
        return result["teamCreate"]["team"]

    async def create_project(
        self, team_id: str, name: str, description: str = None
    ) -> Dict:
        query = """
        mutation CreateProject($teamId: String!, $name: String!, $description: String) {
          projectCreate(input: {teamId: $teamId, name: $name, description: $description}) {
            success
            project {
              id
              name
              description
            }
          }
        }
        """
        variables = {"teamId": team_id, "name": name, "description": description}
        result = await self.execute_query(query, variables)
        return result["projectCreate"]["project"]

    async def create_cycle(
        self, team_id: str, name: str, start_date: str, end_date: str
    ) -> Dict:
        query = """
        mutation CreateCycle($teamId: String!, $name: String!, $startDate: DateTime!, $endDate: DateTime!) {
          cycleCreate(input: {teamId: $teamId, name: $name, startDate: $startDate, endDate: $endDate}) {
            success
            cycle {
              id
              number
              name
              startDate
              endDate
            }
          }
        }
        """
        variables = {
            "teamId": team_id,
            "name": name,
            "startDate": start_date,
            "endDate": end_date,
        }
        result = await self.execute_query(query, variables)
        return result["cycleCreate"]["cycle"]

    async def create_issue(
        self, team_id: str, title: str, description: str = None, **kwargs
    ) -> Dict:
        query = """
        mutation CreateIssue($teamId: String!, $title: String!, $description: String, $assigneeId: String, $projectId: String, $cycleId: String, $parentId: String, $priority: Int, $estimate: Float, $labelIds: [String!]) {
          issueCreate(input: {teamId: $teamId, title: $title, description: $description, assigneeId: $assigneeId, projectId: $projectId, cycleId: $cycleId, parentId: $parentId, priority: $priority, estimate: $estimate, labelIds: $labelIds}) {
            success
            issue {
              id
              title
              description
              assignee { id }
              project { id }
              cycle { id }
              parent { id }
              priority
              estimate
              labels { nodes { id } }
            }
          }
        }
        """
        variables = {
            "teamId": team_id,
            "title": title,
            "description": description,
            **kwargs,
        }
        result = await self.execute_query(query, variables)
        return result["issueCreate"]["issue"]

    async def update_issue(self, issue_id: str, data: Dict[str, Any]) -> Dict:
        query = """
        mutation UpdateIssue($id: String!, $input: IssueUpdateInput!) {
        issueUpdate(id: $id, input: $input) {
            success
            issue {
            id
            title
            description
            state { id name }
            }
        }
        }
        """
        variables = {"id": issue_id, "input": data}
        result = await self.execute_query(query, variables)
        return result["issueUpdate"]["issue"]

    async def create_comment(self, issue_id: str, body: str) -> Dict:
        query = """
        mutation CreateComment($issueId: String!, $body: String!) {
          commentCreate(input: {issueId: $issueId, body: $body}) {
            success
            comment {
              id
              body
              user { id }
              createdAt
            }
          }
        }
        """
        variables = {"issueId": issue_id, "body": body}
        result = await self.execute_query(query, variables)
        return result["commentCreate"]["comment"]

    async def create_attachment(self, issue_id: str, url: str, title: str) -> Dict:
        query = """
        mutation CreateAttachment($issueId: String!, $url: String!, $title: String!) {
          attachmentCreate(input: {issueId: $issueId, url: $url, title: $title}) {
            success
            attachment {
              id
              url
              title
            }
          }
        }
        """
        variables = {"issueId": issue_id, "url": url, "title": title}
        result = await self.execute_query(query, variables)
        return result["attachmentCreate"]["attachment"]

    async def create_issue_relation(
        self, issue_id: str, related_issue_id: str, type: str
    ) -> Dict:
        query = """
        mutation CreateIssueRelation($issueId: String!, $relatedIssueId: String!, $type: IssueRelationType!) {
          issueRelationCreate(input: {issueId: $issueId, relatedIssueId: $relatedIssueId, type: $type}) {
            success
            issueRelation {
              id
              type
            }
          }
        }
        """
        variables = {
            "issueId": issue_id,
            "relatedIssueId": related_issue_id,
            "type": type,
        }
        result = await self.execute_query(query, variables)
        return result["issueRelationCreate"]["issueRelation"]

    async def get_user(self, email: str) -> Dict:
        query = """
        query GetUserByEmail($email: String!) {
          users(filter: { email: { eq: $email } }) {
            nodes {
              id
              name
              email
            }
          }
        }
        """
        variables = {"email": email}
        result = await self.execute_query(query, variables)

        user_nodes = result["users"]["nodes"]
        if len(user_nodes) == 0:
            return None
        return user_nodes[0]

    async def invite_user(self, email: str, team_id: str) -> Dict:
        query = """
        mutation OrganizationInviteCreate($organizationInviteCreateInput: OrganizationInviteCreateInput!) {
          organizationInviteCreate(input: $organizationInviteCreateInput) {
            lastSyncId
          }
        }
        """

        variables = {
            "organizationInviteCreateInput": {
                "email": email,
                "teamIds": [team_id],
                "role": "admin",  # can only invite as admin for free accounts
                "metadata": {"source": "workspace-members-page"},
            }
        }

        result = await self.execute_query(query, variables)
        return result["organizationInviteCreate"]

    async def add_user_to_team(self, user_id: str, team_id: str) -> Dict:
        query = """
        mutation TeamMembershipCreate($teamMembershipCreateInput: TeamMembershipCreateInput!) {
          teamMembershipCreate(input: $teamMembershipCreateInput) {
            lastSyncId
          }
        }
        """
        variables = {
            "teamMembershipCreateInput": {
                "teamId": team_id,
                "userId": user_id,
                "owner": False,
            }
        }
        result = await self.execute_query(query, variables)
        return result["teamMembershipCreate"]

    async def get_or_create_label(
        self, team_id: str, label: str, is_epic: bool
    ) -> Dict:
        query = """
        mutation IssueLabelCreate($issueLabelCreateInput: IssueLabelCreateInput!) {
          issueLabelCreate(input: $issueLabelCreateInput) {
            issueLabel {
              id
              name
              color
            }
          }
        }
        """
        # Choose color based on is_epic flag
        color = "#4ea7fc" if not is_epic else "#9370DB"

        variables = {
            "issueLabelCreateInput": {"name": label, "color": color, "teamId": team_id}
        }
        result = await self.execute_query(query, variables)
        return result["issueLabelCreate"]

    async def get_workflow_states(self, team_id: str) -> List[Dict]:
        query = """
        query GetWorkflowStates($teamId: String!) {
          team(id: $teamId) {
            states {
              nodes {
                id
                name
                type
              }
            }
          }
        }
        """
        variables = {"teamId": team_id}
        result = await self.execute_query(query, variables)
        return result["team"]["states"]["nodes"]

    async def create_workflow_state(
        self,
        team_id: str,
        name: str,
        type: str,
        color_code: str,
        description: str,
    ) -> Dict:
        query = """
        mutation WorkflowStateCreate($workflowStateCreateInput: WorkflowStateCreateInput!) {
          workflowStateCreate(input: $workflowStateCreateInput) {
            lastSyncId
          }
        }
        """
        workflow_state_create_input = {
            "teamId": team_id,
            "name": name,
            "description": description,
            "type": type,
            "color": color_code,
        }
        variables = {"workflowStateCreateInput": workflow_state_create_input}
        result = await self.execute_query(query, variables)
        return result["workflowStateCreate"]
