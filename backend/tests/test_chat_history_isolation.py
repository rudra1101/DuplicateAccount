from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.db_models  # noqa: F401
from app.database.base import Base
from app.db_models.chat_conversation import ChatConversationRecord
from app.db_models.chat_message import ChatMessageRecord
from app.services.chat_ownership_service import (
    clear_owned_conversations,
    ensure_owned_conversation,
    list_owned_conversations,
)


def _conversation(conversation_id: str, user_id: int | None, title: str):
    return ChatConversationRecord(
        id=conversation_id,
        user_id=user_id,
        title=title,
    )


def test_chat_history_is_isolated_by_user():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        db.add_all(
            [
                _conversation("user-1-chat", 101, "User 1 Chat"),
                _conversation("user-2-chat", 202, "User 2 Chat"),
                _conversation("legacy-chat", None, "Legacy Unowned Chat"),
            ]
        )
        db.commit()

        user_1 = list_owned_conversations(db, user_id=101)
        user_2 = list_owned_conversations(db, user_id=202)

        assert [item.id for item in user_1] == ["user-1-chat"]
        assert [item.id for item in user_2] == ["user-2-chat"]

        assert ensure_owned_conversation(
            db,
            conversation_id="user-1-chat",
            user_id=101,
        ).id == "user-1-chat"

        try:
            ensure_owned_conversation(
                db,
                conversation_id="user-2-chat",
                user_id=101,
            )
        except LookupError:
            pass
        else:
            raise AssertionError("A user accessed another user's conversation")

        try:
            ensure_owned_conversation(
                db,
                conversation_id="legacy-chat",
                user_id=101,
            )
        except LookupError:
            pass
        else:
            raise AssertionError("Legacy unowned chat should not be exposed")


def test_clear_history_only_removes_current_users_chats():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        first = _conversation("first", 101, "First")
        second = _conversation("second", 202, "Second")
        db.add_all([first, second])
        db.flush()
        db.add_all(
            [
                ChatMessageRecord(
                    conversation_id="first",
                    role="user",
                    content="hello from user 1",
                    sources=[],
                ),
                ChatMessageRecord(
                    conversation_id="second",
                    role="user",
                    content="hello from user 2",
                    sources=[],
                ),
            ]
        )
        db.commit()

        deleted = clear_owned_conversations(db, user_id=101)
        db.commit()

        assert deleted == 1
        assert list_owned_conversations(db, user_id=101) == []
        assert [item.id for item in list_owned_conversations(db, user_id=202)] == [
            "second"
        ]
