# jira_setup.py

import uuid

from .api import JiraAPI
from .config import Config
from .logger import logger


class JiraSetup:
    def __init__(self, jira_api: JiraAPI):
        self.jira_api = jira_api

    async def setup_global_workflow(self):
        logger.info("Setting up global Jira workflow")
        if Config.GLOBAL_WORKFLOW_SCHEME_ID:
            logger.info("Global workflow already set up")
            return

        pt_statuses = [
            "Unstarted",
            "Started",
            "Finished",
            "Delivered",
            "Rejected",
            "Accepted",
        ]

        # Generate UUIDs for status references
        status_refs = {status: str(uuid.uuid4()) for status in pt_statuses}

        workflow_data = {
            "scope": {"type": "GLOBAL"},
            "statuses": [
                {
                    "name": status,
                    "statusCategory": (
                        "TODO"
                        if status == "Unstarted"
                        else (
                            "IN_PROGRESS"
                            if status in ["Started", "Finished", "Delivered"]
                            else "DONE"
                        )
                    ),
                    "statusReference": status_refs[status],
                    "description": f"{status.lower()} in PT",
                }
                for status in pt_statuses
            ],
            "workflows": [
                {
                    "name": Config.GLOBAL_WORKFLOW_NAME,
                    "description": "Workflow created for Pivotal Tracker migration",
                    "startPointLayout": {"x": 0, "y": 0},
                    "statuses": [
                        {
                            "statusReference": status_refs[status],
                            "layout": {"x": 100 * i, "y": 0},
                            "properties": {},
                        }
                        for i, status in enumerate(pt_statuses)
                    ],
                    "transitions": [
                        {
                            "id": str(i + 1),
                            "name": f"Move to {status}",
                            "description": f"Transition to {status} state",
                            "from": [
                                {"statusReference": status_refs[s]}
                                for s in pt_statuses
                                if s != status
                            ],
                            "to": {"statusReference": status_refs[status]},
                            "type": "DIRECTED",
                            "rules": {},
                            "properties": {},
                        }
                        for i, status in enumerate(pt_statuses)
                    ]
                    + [
                        {
                            "id": str(len(pt_statuses) + 1),
                            "name": "Create",
                            "description": "Initial transition",
                            "from": [],
                            "to": {"statusReference": status_refs["Unstarted"]},
                            "type": "INITIAL",
                            "rules": {},
                            "properties": {},
                        }
                    ],
                }
            ],
        }

        try:
            response = await self.jira_api.create_workflows(workflow_data)
            logger.info("Global Jira workflow created successfully")

            # Store the created workflow ID for later use
            workflow_id = response["workflows"][0]["id"]
            Config.set_global_workflow_id(workflow_id)

            scheme_id = await self.create_workflow_scheme(Config.GLOBAL_WORKFLOW_NAME)
            Config.set_global_workflow_scheme_id(scheme_id)
        except Exception as e:
            logger.error(f"Failed to create global Jira workflow: {str(e)}")
            raise

    async def create_workflow_scheme(self, workflow_name):
        scheme_data = {
            "name": "PT Migration Workflow Scheme",
            "description": "Workflow scheme for Pivotal Tracker migration",
            "defaultWorkflow": workflow_name,
            "issueTypeMappings": {},
        }
        response = await self.jira_api.create_workflow_scheme(scheme_data)
        return response["id"]

    async def setup_global_configurations(self):
        """
        Set up any other global configurations needed for the Jira account.
        """
        logger.info("Setting up global Jira configurations")

        # Any other global configurations can be added here

        logger.info("Global Jira configurations setup completed")

    async def run_global_setup(self):
        """
        Run all global setup operations.
        """
        await self.setup_global_workflow()
        await self.setup_global_configurations()
