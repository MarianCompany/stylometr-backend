from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, JSON, Integer, Float, Text as SQLText, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.session import Base


class UserRole(Base):
    __tablename__ = "user_roles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    nickname: Mapped[str] = mapped_column(String(100), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    role_id: Mapped[int | None] = mapped_column(ForeignKey("user_roles.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    role = relationship("UserRole")
    refresh_tokens = relationship("RefreshToken", back_populates="user")
    profiles = relationship(
        "AuthorProfile",
        foreign_keys="AuthorProfile.user_id",
        back_populates="user",
    )
    texts = relationship("Text", back_populates="user")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    jti: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)

    user = relationship("User", back_populates="refresh_tokens")


class AuthorProfile(Base):
    __tablename__ = "author_profiles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    is_public: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    moderated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    moderation_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    moderation_comment: Mapped[str | None] = mapped_column(String(500), nullable=True)
    moderated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    user = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="profiles",
    )
    moderator = relationship(
        "User",
        foreign_keys=[moderated_by],
    )
    metrics = relationship(
        "ProfileMetrics",
        back_populates="profile",
        uselist=False,
        cascade="all, delete-orphan",
        foreign_keys="ProfileMetrics.profile_id",
    )
    profile_texts = relationship(
        "AuthorProfileText",
        back_populates="profile",
        cascade="all, delete-orphan",
    )
    texts = relationship("Text", secondary="author_profile_texts", viewonly=True)

class ProfileMetrics(Base):
    __tablename__ = "profile_metrics"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    profile_id: Mapped[int] = mapped_column(
        ForeignKey("author_profiles.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    metrics_version: Mapped[int] = mapped_column(nullable=False, default=1)
    core_metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    additional_metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    profile = relationship("AuthorProfile", back_populates="metrics")


class Text(Base):
    __tablename__ = "texts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    content: Mapped[str] = mapped_column(SQLText, nullable=False)
    file_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    char_count: Mapped[int] = mapped_column(Integer, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    user = relationship("User", back_populates="texts")
    profile_links = relationship(
        "AuthorProfileText",
        back_populates="text",
        cascade="all, delete-orphan",
    )
    metrics = relationship(
        "TextMetrics",
        back_populates="text",
        uselist=False,
        cascade="all, delete-orphan",
    )

    @property
    def short_content(self):
        return self.content[:200]


class TextMetrics(Base):
    __tablename__ = "text_metrics"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    text_id: Mapped[int] = mapped_column(ForeignKey("texts.id"), nullable=False, unique=True, index=True)
    word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sentence_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_word_length: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    avg_sentence_length: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    ttr: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    punctuation_ratio: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    noun_ratio: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    verb_ratio: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    adj_ratio: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    pronoun_ratio: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    service_words_ratio: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    unique_words_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    additional_metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    text = relationship("Text", back_populates="metrics")


class AuthorProfileText(Base):
    __tablename__ = "author_profile_texts"
    __table_args__ = (UniqueConstraint("profile_id", "text_id", name="uq_profile_text"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("author_profiles.id"), nullable=False, index=True)
    text_id: Mapped[int] = mapped_column(ForeignKey("texts.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    profile = relationship("AuthorProfile", back_populates="profile_texts")
    text = relationship("Text", back_populates="profile_links")
