# 🤖 The Shift-O-Matic 9000

Tired of scheduling shifts with a spreadsheet, a bottle of aspirin, and the sinking feeling you've been unfair to Bob again? We were too. This is the **Shift-O-Matic 9000**, a web app that turns the soul-crushing sudoku of shift scheduling into a one-click affair.

## 🧐 What's It Do?

You tell it who works for you, what they can do, and when they'd rather be literally anywhere else. You define the jobs that need doing, and—this is the fun part—you tell it how much each job *sucks* using a **Difficulty Multiplier**.

Then you press the big green button.

The app's ridiculously over-engineered algorithm whirs to life, sifts through a billion possibilities, and spits out a fair, balanced, and equitable schedule. It ensures that Bob doesn't get stuck with all the "difficulty 3.0" night shifts while Alice sips lattes on the "difficulty 1.0" day shifts.

## ✨ Key Features

-   ✅ **Fairness-Driven Algorithm:** Balances a "weighted effort" score so everyone shares the load.
-   📊 **Visual Sanity Check:** A pretty bar graph shows you exactly who's working how many *real* hours.
-   🎛️ **Difficulty Sliders:** Quantify the misery of any given job role from `1.0` to `10.0`.
-   📅 **Constraint Management:** Workers can't work on their day off? The app actually listens.
-   📤 **Export to Civilization:** Get your final schedule in CSV or Excel, because some people still live in 2003.

## 🛠️ The Tech Stack 

-   **Backend:** **Python** with **Flask** – The sturdy, no-nonsense engine.
-   **Database:** **SQLAlchemy** (with SQLite) – For remembering everything you told it.
-   **Migrations:** **Flask-Migrate** – The construction crew that rebuilds the database without demolishing it.
-   **Frontend:** **Bootstrap**, **Jinja2**, and a sprinkle of **JavaScript** – To make it look like we hired a designer.
-   **Graphs:** **Chart.js** – For turning boring numbers into pretty, colorful bars.

## 🚀 How to Run This Beast

1.  Clone the repo.
2.  Set up your virtual environment and install dependencies:
    ```bash
    # You'll need to create this file first with `pip freeze > requirements.txt`
    pip install -r requirements.txt
    ```
3.  Apply the database migrations:
    ```bash
    flask db upgrade
    ```
4.  Run the app:
    ```bash
    flask run
    ```
5.  Go to `http://127.0.0.1:5000` and reclaim your sanity.

## 🌐 The Future
Currently, this bad boy runs locally on your machine. But soon, it shall be unleashed upon the World Wide Web, so you can manage schedules from your phone while pretending to listen in a meeting. Stay tuned.
