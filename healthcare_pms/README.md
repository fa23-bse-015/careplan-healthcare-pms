# Smart Healthcare Project Management and Monitoring System

A desktop project-management application for planning and controlling the development of a healthcare software system. It is not a hospital operations or patient-facing application.

## Requirements

- Windows 10/11 with Python 3.10 or newer
- Tkinter included with the standard Windows Python installer
- No third-party runtime packages

## Run

1. Extract the source ZIP to a writable folder.
2. Open a terminal in `healthcare_pms`.
3. Run `python app.py` or double-click `run_app.bat`.
4. The application opens `smart_healthcare_project.sqlite3` beside the program. If it does not exist, the app creates the schema and realistic sample data automatically.

The supplied database opens in the completed approved-change state so the combined AI preliminary diagnosis and mobile application effect is visible immediately. The original baseline is PKR 5,000,000 and 16 weeks; the approved plan is PKR 5,800,000 and 19 weeks. Run the reset command below to recreate the initial Pending state, then select CR-001 under **Scope & WBS** and choose **Approve selected change** to apply the linked requirements, WBS items, two activities, PKR 800,000 estimate, and 15 working days once.

## Restore the initial demonstration state

Close the application, then run:

```text
python seed_demo.py --reset
```

This replaces the selected sample database and returns CR-001 to Pending. Back up any database you want to keep before using `--reset`.

## Build a Windows executable

Install PyInstaller in the build environment, then run this from the source folder:

    build_windows.bat

The executable is written to dist/SmartHealthcarePMS.exe. It stores its SQLite database beside the executable, so place it in a writable folder. The executable does not need Python installed to run.

## Working rules

- Schedule dates use Monday-Friday working days, with no public-holiday calendar. Successors start on the next working day after all predecessor forecasts finish.
- Approved baseline duration and budget are stored in the project record. Current approved budget and duration add only approved change requests.
- Planned progress is linear over each activity's scheduled working days. Planned value uses that percentage; earned value uses budget multiplied by recorded actual completion. Actual cost sums expenditure dated on or before the EVM status date.
- Overall progress is budget weighted across scheduled activity estimates.
- CPI or SPI below 0.95, actual cost more than 10% above earned value, and expenditure above the current budget are displayed as warnings. A zero denominator is shown as N/A.
- Risk score is likelihood multiplied by impact. Likelihood and impact use 1-5 scales. Scores 20-25 are Critical, 12-19 High, 6-11 Moderate, and 1-5 Low.

## Data and files

- `smart_healthcare_project.sqlite3`: persistent demo database
- `schema.sql`: normalized SQLite schema
- `seed_demo.py`: reproducible sample-data setup
- `tests/`: executed calculation and persistence tests
- `screenshots/`: screenshots captured from the running desktop application

## Notes

All dates, actual progress, actual expenses, task estimates, and risk ratings in the demonstration dataset are implementation assumptions. The two proposed change impacts combine to the case-study total; they are not applied separately to each deliverable. The proposed AI module is a project deliverable to manage; no medical diagnosis model is implemented.
