from src.configs.database import DATABASE_NAME

MODEL_MODULES = [
    "src.modules.account.models",
    # Add new model modules here
]

TORTOISE_ORM = {
    "connections": {
        "default": f"sqlite://{DATABASE_NAME}",
    },
    "apps": {
        "models": {
            "models": [*MODEL_MODULES, "aerich.models"],
            "default_connection": "default",
        }
    },
    "use_tz": True,
    "timezone": "Africa/Lagos",
}

