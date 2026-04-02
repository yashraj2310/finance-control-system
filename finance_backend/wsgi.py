from finance_backend.app import create_app
from finance_backend.config import AppConfig


application = create_app(AppConfig.from_env())
