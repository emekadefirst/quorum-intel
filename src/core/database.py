from src.configs.database import DATABASE_NAME




TORTOISE_ORM = {
    "connections": {
        "default": f"sqlite://{DATABASE_NAME}",
    },
    "apps": {
        "models": {
            "models": ["src.core.models"],
            "default_connection": "default",
                "migrations": "migrations",
        }
    },
    "use_tz": True,
    "timezone": "Africa/Lagos",
}

