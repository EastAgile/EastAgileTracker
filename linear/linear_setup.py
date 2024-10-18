# linear/linear_setup.py

from .api import LinearAPI
from .config import Config
from .exceptions import ConfigurationError
from .logger import logger
from .models import LinearWorkflowState


class LinearSetup:
    def __init__(self, linear_api: LinearAPI):
        self.linear_api = linear_api

    async def setup_workflow_states(self, team_id: str):
        """
        Set up the workflow states for a team in Linear to match Pivotal Tracker states.
        """
        logger.info(f"Setting up workflow states for team {team_id}")

        # Define the workflow states we want to ensure exist, along with a nice pastel-like color
        required_states = [
            ("Unstarted", "unstarted", "#FFB3BA"),  # Light Pink
            ("Started", "started", "#FFDFBA"),  # Peach
            ("Finished", "started", "#FFFFBA"),  # Light Yellow
            ("Delivered", "completed", "#BAFFC9"),  # Light Mint Green
            ("Accepted", "completed", "#BAE1FF"),  # Light Sky Blue
            ("Rejected", "unstarted", "#DFBAFF"),  # Light Lavender
        ]

        existing_states = await self.linear_api.get_workflow_states(team_id)
        existing_state_names = {state["name"].lower() for state in existing_states}

        for state_name, state_type, color_code in required_states:
            if state_name.lower() not in existing_state_names:
                try:
                    new_state = await self.linear_api.create_workflow_state(
                        team_id,
                        state_name,
                        state_type,
                        color_code,
                        f"PT {state_name.lower()} state",
                    )
                    logger.info(f"Created new workflow state: {state_name}")
                except Exception as e:
                    logger.error(
                        f"Failed to create workflow state {state_name}: {str(e)}"
                    )
                    raise ConfigurationError(
                        f"Failed to create workflow state {state_name}: {str(e)}"
                    )

        logger.info("Workflow states setup completed")

    async def setup_team(
        self, pt_project_name: str, pt_project_description: str = None
    ):
        """
        Set up a team in Linear based on a Pivotal Tracker project.
        """
        logger.info(f"Setting up team for project: {pt_project_name}")

        # Generate a key for the team (first letter of the first 4 words)
        key = "".join(word[0].upper() for word in pt_project_name.split()[:4])

        try:
            team = await self.linear_api.create_team(
                pt_project_name, key, pt_project_description
            )
            logger.info(f"Created new team: {team['name']} (ID: {team['id']})")

            # Set up workflow states for the new team
            await self.setup_workflow_states(team["id"])

            return team
        except Exception as e:
            logger.error(
                f"Failed to create team for project {pt_project_name}: {str(e)}"
            )
            raise ConfigurationError(
                f"Failed to create team for project {pt_project_name}: {str(e)}"
            )

    async def run_global_setup(self):
        """
        Run any global setup operations needed for the Linear workspace.
        """
        logger.info("Running global setup for Linear workspace")

        # Add any global setup operations here
        # For example, setting up custom fields, if needed

        logger.info("Global setup completed")

    async def setup_labels(self, team_id: str, pt_labels: list):
        """
        Set up labels in Linear based on Pivotal Tracker labels.
        """
        logger.info(f"Setting up labels for team {team_id}")

        for label_name, is_epic in pt_labels:
            try:
                label = await self.linear_api.get_or_create_label(
                    team_id, label_name, is_epic
                )
                logger.info(f"Created or found label: {label_name}")
            except Exception as e:
                logger.error(f"Failed to create label {label_name}: {str(e)}")
                # Continue with the next label instead of raising an exception

        logger.info("Labels setup completed")
