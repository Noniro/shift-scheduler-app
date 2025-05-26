# from app import create_app, db
# from app.models import User, SchedulingPeriod, JobRole, ShiftDefinition, Worker, Constraint, ScheduledShift # Added JobRole

# app = create_app()

# @app.shell_context_processor
# def make_shell_context():
#     return {
#         'db': db,
#         'User': User,
#         'SchedulingPeriod': SchedulingPeriod,
#         'JobRole': JobRole, # Added
#         'ShiftDefinition': ShiftDefinition,
#         'Worker': Worker,
#         'Constraint': Constraint,
#         'ScheduledShift': ScheduledShift
#     }

# if __name__ == '__main__':
#     app.run(debug=True)

# run.py

from app import create_app, db
from app.models import User, SchedulingPeriod, JobRole, ShiftDefinition, Worker, Constraint, ScheduledShift # Added JobRole
import webbrowser
from threading import Timer
import os # To check for Werkzeug reloader

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'User': User,
        'SchedulingPeriod': SchedulingPeriod,
        'JobRole': JobRole, # Added
        'ShiftDefinition': ShiftDefinition,
        'Worker': Worker,
        'Constraint': Constraint,
        'ScheduledShift': ScheduledShift
    }

def open_browser():
    """Opens the default web browser to the Flask app's URL."""
    # Ensure this URL matches what app.run() will use
    webbrowser.open_new_tab("http://127.0.0.1:5000/")



# Ensure the script runs only when executed directly, not when imported
# For running use `python run.py` or `flask run` if FLASK_APP is set to this file
if __name__ == '__main__':
    # Define host and port to ensure consistency
    HOST = '127.0.0.1'
    PORT = 5000

    # TODO add --input "ip:port" to run.py

    # When using Flask's reloader (debug=True), app.run() is called twice.
    # The first time in the main process, and the second time in a child process.
    # We only want to open the browser from the main process.
    # Werkzeug sets WERKZEUG_RUN_MAIN to 'true' in the reloaded subprocess.
    # So, if it's not set, or not 'true', this is the initial launch.
    if not os.environ.get("WERKZEUG_RUN_MAIN"):
        # Open the browser after a short delay to give the server time to start.
        # 1 second should generally be enough for a local dev server.
        Timer(1, open_browser).start()

    app.run(debug=True, host=HOST, port=PORT, use_reloader=True)
    # By default, debug=True implies use_reloader=True. Explicitly setting it for clarity.
    # If you set use_reloader=False, the WERKZEUG_RUN_MAIN check is less critical
    # but still good practice.