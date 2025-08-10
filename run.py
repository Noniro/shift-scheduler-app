import os
import sys
import webbrowser
from threading import Timer
from waitress import serve
from app import create_app, db

# Create the Flask app instance
app = create_app()

# Function to ensure the database is created
def setup_database(app_instance):
    with app_instance.app_context():
        # This checks if the db file exists. If not, it creates it and the tables.
        # This is crucial for the first time a user runs the .exe
        if not os.path.exists(os.path.join(os.path.dirname(__file__), 'app.db')):
             print("Database not found, creating a new one...")
             db.create_all()
             print("Database created.")
        else:
             print("Database already exists.")


# Function to open the browser
def open_browser():
    # Opens the URL in a new tab
      webbrowser.open_new("http://127.0.0.1:8080")

if __name__ == '__main__':
    # Set up the database within the app context
    setup_database(app)

    # Open the web browser 1 second after the server starts
    Timer(1, open_browser).start()

    # Start the Waitress server
    print("Starting server on http://127.0.0.1:8080")
    serve(app, host='127.0.0.1', port=8080)