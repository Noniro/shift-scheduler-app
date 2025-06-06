import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Configuration class for the Flask application of sqlalchemy
# This class contains settings for the application, including the secret key,
# database URI, and session lifetime, and sql configurations.
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'replace-this-with-a-very-strong-random-secret-key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(BASE_DIR, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = os.environ.get('PERMANENT_SESSION_LIFETIME') or 30 * 24 * 60 * 60 # 30 days in seconds