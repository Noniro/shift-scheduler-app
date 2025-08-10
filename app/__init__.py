import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config
from datetime import timedelta

# Helper function to find the correct path for bundled files
def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # For development, use the normal directory structure
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

db = SQLAlchemy()
migrate = Migrate() # We can keep this for local development

def create_app(config_class=Config):
    # --- THIS IS THE KEY CHANGE ---
    # We define the paths dynamically so PyInstaller can find them
    template_dir = get_resource_path('app/templates')
    static_dir = get_resource_path('app/static')

    # Pass these paths to the Flask app constructor
    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
    
    app.config.from_object(config_class)

    if isinstance(app.config.get('PERMANENT_SESSION_LIFETIME'), (int, float)):
         app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(seconds=app.config['PERMANENT_SESSION_LIFETIME'])

    db.init_app(app)
    migrate.init_app(app, db) # Initialize migrate

    from . import models

    from .routes import main_bp
    app.register_blueprint(main_bp)

    return app