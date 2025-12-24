from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .config import get_settings
from .db import Base


settings = get_settings()


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    model_name: Mapped[str] = mapped_column(String, default=settings.default_model)
    has_access: Mapped[bool] = mapped_column(Boolean, default=False)
    stars_balance: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    messages: Mapped[list["Message"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    transactions: Mapped[list["StarsTransaction"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String)
    content: Mapped[str] = mapped_column(String)
    model_name: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    user: Mapped[User] = relationship(back_populates="messages")


class StarsTransaction(Base):
    __tablename__ = "stars_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[str] = mapped_column(String)
    stars_amount: Mapped[int] = mapped_column(Integer)
    payload: Mapped[str] = mapped_column(String)
    currency: Mapped[str] = mapped_column(String)
    tg_charge_id: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    user: Mapped[User] = relationship(back_populates="transactions")
