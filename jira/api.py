# jira/api.py

import asyncio

import aiohttp
from aiohttp import ClientResponseError

from .config import Config
from .exceptions import JiraAPIError, RateLimitError


class JiraAPI:
    def __init__(self):
        self.base_url = Config.JIRA_URL
        self.auth = aiohttp.BasicAuth(Config.JIRA_EMAIL, Config.JIRA_API_TOKEN)
        self.session = aiohttp.ClientSession(auth=self.auth)

    async def close(self):
        if self.session:
            await self.session.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def _request(
        self,
        method,
        endpoint,
        data=None,
        files=None,
        params=None,
        api_version=3,
        url=None,
        headers=None,
    ):
        if not url:
            url = f"{self.base_url}/rest/api/{api_version}/{endpoint}"

        # Initialize headers if not provided
        if headers is None:
            headers = {}

        for attempt in range(Config.MAX_RETRIES):
            try:
                if isinstance(data, aiohttp.FormData):
                    # For file uploads, don't set Content-Type
                    headers["X-Atlassian-Token"] = "no-check"
                    async with self.session.request(
                        method, url, data=data, params=params, headers=headers
                    ) as response:
                        if response.status >= 400:
                            error_body = await response.text()
                            raise ClientResponseError(
                                response.request_info,
                                response.history,
                                status=response.status,
                                message=f"{response.reason}: {error_body}",
                                headers=response.headers,
                            )
                        if response.status == 204:
                            return None
                        return await response.json()
                else:
                    # For regular JSON requests
                    async with self.session.request(
                        method, url, json=data, params=params, headers=headers
                    ) as response:
                        if response.status >= 400:
                            error_body = await response.text()
                            raise ClientResponseError(
                                response.request_info,
                                response.history,
                                status=response.status,
                                message=f"{response.reason}: {error_body}",
                                headers=response.headers,
                            )
                        if response.status == 204:
                            return None
                        return await response.json()
            except ClientResponseError as e:
                if e.status == 429:  # Too Many Requests
                    retry_after = int(
                        e.headers.get("Retry-After", Config.RATE_LIMIT_PAUSE)
                    )
                    await asyncio.sleep(retry_after)
                    continue
                raise JiraAPIError(
                    f"HTTP Error: {e.status}, message='{e.message}', url='{e.request_info.url}'"
                )
            except aiohttp.ClientError as e:
                if attempt == Config.MAX_RETRIES - 1:
                    raise JiraAPIError(
                        f"Request failed after {Config.MAX_RETRIES} attempts: {e}"
                    )
                await asyncio.sleep(Config.RATE_LIMIT_PAUSE)

        raise RateLimitError("Rate limit exceeded and max retries reached")

    async def create_project(self, key, name, description):
        data = {
            "key": key,
            "name": name,
            "projectTypeKey": "software",
            "description": description,
            "assigneeType": "UNASSIGNED",
            "leadAccountId": Config.JIRA_ACCOUNT_ID,
            "issueTypeScheme": Config.JIRA_ISSUE_TYPE_SCHEME,
        }
        return await self._request("POST", "project", data=data)

    async def create_epic(self, project_key, summary, description=None):
        data = {
            "fields": {
                "project": {"key": project_key},
                "summary": summary,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"text": description, "type": "text"}],
                        }
                    ],
                },
                "issuetype": {"name": "Epic"},
            }
        }
        return await self._request("POST", "issue", data=data)

    async def create_issue(
        self, project_key, issue_type, summary, description=None, fields=None
    ):
        data = {
            "fields": {
                "project": {"key": project_key},
                "summary": summary,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"text": description or "", "type": "text"}],
                        }
                    ],
                },
                "issuetype": {"name": issue_type},
            }
        }
        if fields:
            data["fields"].update(fields)

        return await self._request("POST", "issue", data=data)

    async def create_subtask(self, parent_key, summary, description=None, fields=None):
        project_key = parent_key.split("-")[0]
        data = {
            "fields": {
                "project": {"key": project_key},
                "parent": {"key": parent_key},
                "summary": summary,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"text": description or "", "type": "text"}],
                        }
                    ],
                },
                "issuetype": {"name": "Sub-task"},
            }
        }
        if fields:
            data["fields"].update(fields)

        return await self._request("POST", "issue", data=data)

    async def update_issue(self, issue_key, fields):
        data = {"fields": fields}
        return await self._request("PUT", f"issue/{issue_key}", data=data)

    async def create_comment(self, issue_key, body):
        data = {"body": body}
        return await self._request(
            "POST", f"issue/{issue_key}/comment", data=data, api_version=2
        )

    async def add_attachment(self, issue_key, file_path, filename):
        data = aiohttp.FormData()
        data.add_field("file", open(file_path, "rb"), filename=filename)
        return await self._request("POST", f"issue/{issue_key}/attachments", data=data)

    async def create_user(self, email):
        data = {"emailAddress": email, "products": ["jira-software"]}
        return await self._request("POST", "user", data=data)

    async def update_user(self, email, active):
        data = {"active": active}
        return await self._request("PUT", f"user?key={email}", data=data)

    async def get_project(self, project_key):
        return await self._request("GET", f"project/{project_key}")

    async def get_issue(self, issue_key):
        return await self._request("GET", f"issue/{issue_key}")

    async def search_issues(self, jql, start_at=0, max_results=50, fields=None):
        params = {"jql": jql, "startAt": start_at, "maxResults": max_results}
        if fields:
            params["fields"] = ",".join(fields)
        return await self._request("GET", "search", params=params)

    async def create_status(self, name, description="", category="TO_DO"):
        status_data = {
            "name": name,
            "description": description,
            "statusCategory": category,
        }
        return await self._request("POST", "status", data=status_data)

    async def create_sprint(self, sprint_data):
        url = f"{self.base_url}/rest/agile/1.0/sprint"
        return await self._request("POST", "sprint", data=sprint_data, url=url)

    async def add_issues_to_sprint(self, sprint_id, issue_keys):
        url = f"{self.base_url}/rest/agile/1.0/sprint/{sprint_id}/issue"
        data = {"issues": issue_keys}
        return await self._request(
            "POST", f"sprint/{sprint_id}/issue", data=data, url=url
        )

    async def add_attachment_to_issue(self, issue_key, form_data):
        return await self._request(
            "POST", f"issue/{issue_key}/attachments", data=form_data
        )

    async def get_user(self, email):
        try:
            return await self._request("GET", f"user/search?query={email}")
        except JiraAPIError as e:
            if e.status_code == 404:
                return None
            raise

    async def transition_issue(self, issue_key, status):
        # Get available transitions
        response = await self._request("GET", f"issue/{issue_key}/transitions")
        available_transitions = response.get("transitions", [])

        # Find the transition ID for the desired status
        transition_id = None
        for transition in available_transitions:
            if transition["to"]["name"].lower() == status.lower():
                transition_id = transition["id"]
                break

        if not transition_id:
            raise JiraAPIError(f"Transition to status '{status}' not found.")

        return await self._request(
            "POST",
            f"issue/{issue_key}/transitions",
            data={"transition": {"id": transition_id}},
        )

    async def create_filter_for_project(self, project_key):
        data = {
            "name": f"All Issues in {project_key}",
            "jql": f"project = {project_key}",
            "description": f"A filter for all issues in the {project_key} project",
            "favourite": True,
        }
        return await self._request("POST", "filter", data=data)

    async def create_board(self, project_key, filter_id):
        url = f"{self.base_url}/rest/agile/1.0/board"
        data = {
            "name": f"{project_key} Agile Board",
            "type": "scrum",
            "location": {"type": "project", "projectKeyOrId": project_key},
            "filterId": filter_id,
        }
        return await self._request("POST", "board", data=data, url=url)

    async def link_issue_to_epic(self, issue_key, epic_key):
        data = {"fields": {"parent": {"key": epic_key}}}
        return await self._request("PUT", f"issue/{issue_key}", data=data)

    async def create_blocker_link(self, blocker_key, blocked_key):
        data = {
            "type": {"name": "Blocks"},
            "inwardIssue": {"key": blocker_key},
            "outwardIssue": {"key": blocked_key},
        }
        return await self._request("POST", "issueLink", data=data)

    async def create_workflows(self, workflow_data):
        return await self._request(
            "POST", "workflows/create", data=workflow_data, api_version=3
        )

    async def create_workflow_scheme(self, scheme_data):
        return await self._request("POST", "workflowscheme", data=scheme_data)

    async def assign_workflow_scheme_to_project(self, project_id, scheme_id):
        data = {"workflowSchemeId": scheme_id, "projectId": project_id}
        return await self._request(
            "PUT",
            f"workflowscheme/project",
            data=data,
        )

    # async def delete_issue_type_screen_scheme(self, scheme_id):
    #     return await self._request("DELETE", f"issuetypescreenscheme/{scheme_id}")

    # async def delete_screen_scheme(self, scheme_id):
    #     return await self._request("DELETE", f"screenscheme/{scheme_id}")

    # async def delete_screen(self, screen_id):
    #     return await self._request("DELETE", f"screens/{screen_id}")

    async def get_issue_screen_ids(self, project_key):
        screen_data = await self._request(
            "GET", f"screens?queryString={project_key}&maxResults=2000"
        )
        screens = screen_data["values"]

        # Each project has 3 matching screens, we need to take the first and second one which is the create and edit issue screen
        return [screens[len(screens) - 3]["id"], screens[len(screens) - 2]["id"]]

    async def get_screen_tab_id(self, screen_id):
        tab_data = await self._request("GET", f"screens/{screen_id}/tabs")
        return tab_data[0]["id"]

    async def add_custom_field_to_screen_tab(self, screen_id, tab_id, field_id):
        data = {"fieldId": field_id}
        return await self._request(
            "POST", f"screens/{screen_id}/tabs/{tab_id}/fields", data=data
        )

    async def get_project_role_id(self, project_key, role_name):
        roles_map = await self._request("GET", f"project/{project_key}/role")
        if role_name in roles_map:
            return roles_map[role_name].split("/")[-1]
        return None

    async def add_user_to_project_role(self, project_key, role_id, user_id):
        data = {"user": [user_id]}
        return await self._request(
            "POST", f"project/{project_key}/role/{role_id}", data=data
        )
