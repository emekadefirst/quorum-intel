import os

from dotenv import load_dotenv

load_dotenv()

JWT_ACCESS_EXPIRY = int(os.getenv("JWT_ACCESS_EXPIRY", "15"))
JWT_REFRESH_EXPIRY = int(os.getenv("JWT_REFRESH_EXPIRY", "7"))
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_SECRET = os.getenv("JWT_ACCESS_SECRET", "")
JWT_REFRESH_SECRET = os.getenv("JWT_REFRESH_SECRET", "")
