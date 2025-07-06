from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config
from datetime import timedelta
from flask_migrate import Migrate  # <-- 1. IMPORT IT

db = SQLAlchemy()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    if isinstance(app.config.get('PERMANENT_SESSION_LIFETIME'), (int, float)):
         app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(seconds=app.config['PERMANENT_SESSION_LIFETIME'])

    db.init_app(app)
    migrate = Migrate(app, db)  # <-- 2. INITIALIZE IT

    from . import models

    from .routes import main_bp
    app.register_blueprint(main_bp)

    return app