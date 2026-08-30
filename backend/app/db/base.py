from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from backend.app.models.source import Source  # noqa: E402,F401
