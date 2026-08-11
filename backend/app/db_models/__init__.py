from app.db_models.account import AccountRecord
from app.db_models.duplicate_candidate import DuplicateCandidateRecord
from app.db_models.duplicate_group import DuplicateGroupRecord
from app.db_models.integration import IntegrationRecord
from app.db_models.job_execution import JobExecutionRecord
from app.db_models.job_schedule import JobScheduleRecord
from app.db_models.scan import ScanRecord
from app.db_models.duplicate_training_label import (
    DuplicateTrainingLabelRecord,
)

__all__ = [
    "AccountRecord",
    "DuplicateCandidateRecord",
    "DuplicateGroupRecord",
    "IntegrationRecord",
    "JobExecutionRecord",
    "JobScheduleRecord",
    "DuplicateTrainingLabelRecord"
    "ScanRecord",
]