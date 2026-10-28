
# MIS Report Automation

## Overview
This project automates the generation of Daily and Weekly MIS reports using Python and PostgreSQL.

## Project Structure

- `daily_mis_report.py` - Executes daily MIS report automation.
- `weekly_mis_report.py` - Executes weekly MIS report automation.
- `requirements.txt` - Lists the Python dependencies.
- `.env` - Stores database configuration locally. Do not upload this file.
- `Student.xlsx` - Generated Excel report, if applicable.

## Prerequisites

- Python 3.10 or later
- PostgreSQL
- Git

## Setup Instructions

### 1. Clone the repository

```bash
git clone YOUR_GITHUB_REPOSITORY_URL
cd MIS_Reports
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it on Windows:

```powershell
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure database credentials

Create a local `.env` file and add the environment variable names expected by the Python scripts.

Do not share passwords or commit `.env` to GitHub.

### 5. Run the reports

Daily report:

```bash
python daily_mis_report.py
```

Weekly report:

```bash
python weekly_mis_report.py
```

## Notes

- Configure PostgreSQL before running the scripts.
- Ensure the required database tables and stored procedures exist.
- Generated reports depend on the database configuration and source data.
