export interface KnowledgeDocument {
  id: number;
  name: string;
  originalFilename: string;
  contentType: string | null;
  status: string;
  chunkCount: number;
  characterCount: number;
  errorMessage: string | null;
  createdAt: string | null;
  updatedAt: string | null;
}

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ??
  "http://127.0.0.1:8000/api";


export async function getKnowledgeDocuments(): Promise<
  KnowledgeDocument[]
> {
  const response = await fetch(
    `${API_BASE_URL}/knowledge/documents`
  );

  if (!response.ok) {
    throw new Error(
      "Failed to load knowledge documents."
    );
  }

  const data = await response.json();

  if (Array.isArray(data)) {
    return data;
  }

  if (Array.isArray(data.documents)) {
    return data.documents;
  }

  return [];
}


export async function getKnowledgeDocument(
  documentId: number
): Promise<KnowledgeDocument> {
  const response = await fetch(
    `${API_BASE_URL}/knowledge/documents/${documentId}`
  );

  if (!response.ok) {
    throw new Error(
      "Failed to load knowledge document."
    );
  }

  return response.json();
}


export async function uploadKnowledgeDocument(
  file: File,
  name?: string
): Promise<unknown> {
  const formData = new FormData();

  formData.append(
    "file",
    file
  );

  if (name?.trim()) {
    formData.append(
      "name",
      name.trim()
    );
  }

  const response = await fetch(
    `${API_BASE_URL}/knowledge/upload`,
    {
      method: "POST",
      body: formData,
    }
  );

  if (!response.ok) {
    const errorData = await response
      .json()
      .catch(() => null);

    throw new Error(
      errorData?.detail ??
      "Failed to upload knowledge document."
    );
  }

  return response.json();
}


export async function deleteKnowledgeDocument(
  documentId: number
): Promise<void> {
  const response = await fetch(
    `${API_BASE_URL}/knowledge/documents/${documentId}`,
    {
      method: "DELETE",
    }
  );

  if (!response.ok) {
    const errorData = await response
      .json()
      .catch(() => null);

    throw new Error(
      errorData?.detail ??
      "Failed to delete knowledge document."
    );
  }
}