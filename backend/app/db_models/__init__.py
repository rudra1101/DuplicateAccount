from app.db_models.account import AccountRecord
from app.db_models.duplicate_candidate import DuplicateCandidateRecord
from app.db_models.duplicate_group import DuplicateGroupRecord
from app.db_models.integration import IntegrationRecord
from app.db_models.job_execution import JobExecutionRecord
from app.db_models.job_schedule import JobScheduleRecord
from app.db_models.scan import ScanRecord
from app.db_models.duplicate_training_label import DuplicateTrainingLabelRecord
from app.db_models.knowledge_chunk import KnowledgeChunkRecord
from app.db_models.knowledge_document import KnowledgeDocumentRecord
from app.db_models.chat_conversation import ChatConversationRecord
from app.db_models.chat_message import ChatMessageRecord
from app.db_models.chat_feedback import ChatFeedbackRecord
from app.db_models.permission import PermissionRecord
from app.db_models.role import RoleRecord
from app.db_models.role_permission import RolePermissionRecord
from app.db_models.user import UserRecord

__all__ = [
    "AccountRecord",
    "DuplicateCandidateRecord",
    "DuplicateGroupRecord",
    "IntegrationRecord",
    "JobExecutionRecord",
    "JobScheduleRecord",
    "DuplicateTrainingLabelRecord",
    "ScanRecord",
    "KnowledgeChunkRecord",
    "KnowledgeDocumentRecord",
    "ChatConversationRecord",
    "ChatMessageRecord",
    "ChatFeedbackRecord",
    "PermissionRecord",
    "RoleRecord",
    "RolePermissionRecord",
    "UserRecord",
]
