# Shift Scheduler Application

The Shift Scheduler is a web-based application designed to automate and simplify the process of creating and managing employee work schedules. It provides a robust platform for defining scheduling periods, job roles, and worker availability.

The core of the application is a fair-share scheduling algorithm designed to distribute workload equitably among employees. It takes into account worker qualifications, unavailability constraints, and the inherent difficulty of each job role to generate an optimized and balanced schedule.

## Download the Application

For users who want to run the application without installing Python or any dependencies, a standalone executable for Windows is available.

**➡️ [Download the latest release here](https://github.com/YOUR_USERNAME/YOUR_REPO_NAME/releases)**

1.  Navigate to the link above to find the latest version.
2.  Download the `Shift.Scheduler.exe` file from the "Assets" section.
3.  Double-click the file to run the application. No installation is needed.
4.  Your default web browser will automatically open with the application running.

**Note:** The application is built for 64-bit Windows. Your antivirus may flag the unsigned executable; you may need to add an exception to run it.

## Key Features

-   **Fairness-Driven Scheduling Algorithm:** Utilizes a weighted-effort metric to ensure a balanced distribution of demanding shifts across all employees.
-   **Visual Workload Analytics:** A dashboard bar chart provides an at-a-glance summary of the total hours assigned to each worker.
-   **Customizable Job Roles:** Define roles with specific parameters, including number of staff needed, standard shift duration, and a "Difficulty Multiplier" to quantify role intensity.
-   **Comprehensive Constraint Management:** Manage worker qualifications, set unavailability for vacations or appointments, and define maximum work hours per period.
-   **Data Export:** Export generated schedules to CSV or Excel formats for easy distribution and record-keeping.

## For Developers: Running from Source

These instructions are for developers who wish to run the application from the source code.

### Prerequisites

-   Python 3.12
-   Git

### Setup Instructions

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
    cd YOUR_REPO_NAME
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    # For Windows
    python -m venv venv
    .\venv\Scripts\activate

    # For macOS/Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install the required dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Initialize and upgrade the database:**
    ```bash
    flask db upgrade
    ```

5.  **Run the application:**
    ```bash
    flask run
    ```
    The application will be available at `http://127.0.0.1:5000`.

## Technology Stack

-   **Backend:** Python, Flask
-   **Database:** SQLAlchemy ORM with SQLite (for development)
-   **Database Migrations:** Flask-Migrate
-   **Frontend:** Bootstrap, Jinja2, JavaScript
-   **Charting Library:** Chart.js
-   **Executable Bundler:** PyInstaller (on the `desktop-app` branch)

## Future Work

This project has two primary development tracks:
1.  **Web-Based Service (on the `main` branch):** The long-term goal is to deploy the application as a full-fledged web service, allowing for multi-user access and centralized management.
2.  **Standalone Desktop Application (on the `desktop-app` branch):** Continued development of the easy-to-distribute executable for single-user offline use.

Potential future enhancements include:
-   A worker self-service portal for viewing schedules and requesting time off.
-   An advanced, preference-based scheduling algorithm.
-   Integration with calendar services like Google Calendar.
-   A dedicated mobile application for workers.

---

**Important:** Remember to replace both instances of `https://github.com/YOUR_USERNAME/YOUR_REPO_NAME` with the actual URL of your GitHub repository.
