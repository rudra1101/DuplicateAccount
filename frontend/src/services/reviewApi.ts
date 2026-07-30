const BASE_URL = "http://localhost:8000/api";

export async function getReviewQueue() {

    const response = await fetch(
        `${BASE_URL}/review/`
    );

    return response.json();

}