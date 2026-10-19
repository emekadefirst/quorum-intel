from argon2 import PasswordHasher


class PasswordManager:
    ph = PasswordHasher()

    @classmethod
    def set_password(cls, password: str):
        return cls.ph.hash(password)

    @classmethod
    def check_password(cls, hashed: str, password: str):
        try:
            return cls.ph.verify(hashed, password)
        except Exception:
            raise ValueError("Invalid password!")
