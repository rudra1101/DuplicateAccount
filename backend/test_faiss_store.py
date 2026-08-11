import json

from app.ai.embeddings import (
    embedding_service,
)
from app.ai.vector_store import (
    FaissVectorStore,
    VectorMetadata,
)


store = FaissVectorStore(
    index_filename=(
        "test_accounts.faiss"
    ),
    metadata_filename=(
        "test_accounts_metadata.json"
    ),
)

store.clear()

texts = [
    "William Thompson Human Resources",
    "Bill Thompson HR",
    "Rachel Green Finance",
]

vectors = embedding_service.embed_many(
    texts
)

metadata = [
    VectorMetadata(
        vector_id=1,
        scan_id=1,
        source_account_id="HR-100",
        application="Workday",
        username="william.thompson",
        display_name="William Thompson",
        email="william.thompson@company.com",
        employee_id="EMP9001",
        embedding_model=(
            embedding_service.model
        ),
        extra={},
    ),
    VectorMetadata(
        vector_id=2,
        scan_id=1,
        source_account_id="AD-900",
        application="Active Directory",
        username="bill.thompson",
        display_name="Bill Thompson",
        email="bill.thompson@company.com",
        employee_id="EMP9001",
        embedding_model=(
            embedding_service.model
        ),
        extra={},
    ),
    VectorMetadata(
        vector_id=3,
        scan_id=1,
        source_account_id="SAP-200",
        application="SAP",
        username="rachel.green",
        display_name="Rachel Green",
        email="rachel.green@company.com",
        employee_id="EMP2000",
        embedding_model=(
            embedding_service.model
        ),
        extra={},
    ),
]

store.add(
    vectors=vectors,
    metadata=metadata,
)

query_vector = (
    embedding_service.embed(
        "William Thompson HR"
    )
)

results = store.search(
    query_vector=query_vector,
    limit=3,
    minimum_similarity=0.40,
)

print(
    json.dumps(
        [
            result.to_dict()
            for result in results
        ],
        indent=2,
    )
)