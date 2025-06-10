import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'clave-secreta-super-segura'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///skolays.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
