# Pivotal Tracker Data Exporter

This application allows you to export data from Pivotal Tracker projects to a local SQLite database.

## Installation

Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate # On Windows, use venv\Scripts\activate
```

Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

Before using the application, you need to configure your Pivotal Tracker API token via `PIVOTAL_TRACKER_API_TOKEN` in the .env file.

## Usage

To run the ETL process:

To process all accessible projects:
```bash
python main.py run
```

To process specific projects:
```bash
python main.py run -p PROJECT_ID1 -p PROJECT_ID2
```

Using the `--clear` argument can help if there are issues in previous runs:
```bash
python main.py run --clear
```

Replace PROJECT_ID1, PROJECT_ID2, etc., with the actual project IDs you want to process.

## Output

The application will create a SQLite database file named pivotal_tracker_data.db in the same directory as the script. File attachments will be saved in the attachments directory.

## Notes

- The ETL process may take some time depending on the number and size of the projects being processed.
- Ensure you have sufficient disk space for the database and file attachments.
- The application implements rate limiting to avoid overwhelming the Pivotal Tracker API.

## Troubleshooting

If you encounter any issues, please check the following:

- Ensure your API token is correctly configured.
- Check your internet connection.
- Verify that you have the necessary permissions to access the projects you're trying to process.
- If problems persist, please open an issue on the GitHub repository.