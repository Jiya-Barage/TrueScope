
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function getErrorMessage(response) {
  const statusMessage = `Request failed with status ${response.status}`;

  try {
    const responseText = await response.text();
    if (!responseText.trim()) return statusMessage;

    let errorData;
    try {
      errorData = JSON.parse(responseText);
    } catch {
      return `${statusMessage}: ${responseText.trim()}`;
    }

    const detail = errorData?.detail;
    let message;
    if (typeof detail === "string") {
      message = detail;
    } else if (detail && typeof detail === "object") {
      message =
        (typeof detail.message === "string" && detail.message) ||
        (typeof detail.code === "string" && detail.code) ||
        JSON.stringify(detail);
    } else if (typeof errorData?.message === "string") {
      message = errorData.message;
    }

    return message ? `${statusMessage}: ${message}` : statusMessage;
  } catch {
    return statusMessage;
  }
}

// Reusable function for communicating with the backend
export async function apiRequest(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;

  const headers = {
    ...options.headers,
  };

  // FormData sets its own Content-Type, including the required boundary.
  if (!(options.body instanceof FormData) && options.body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  let response;

  try {
    response = await fetch(url, {
      ...options,
      headers,
    });
  } catch {
    throw new Error(
      "Could not connect to the TrueScope backend. Please check whether the server is running."
    );
  }

  if (!response.ok) {
    throw new Error(await getErrorMessage(response));
  }

  // Handle responses that contain no body.
  if (response.status === 204) {
    return null;
  }

  const contentType = response.headers.get("content-type") || "";

  if (contentType.includes("application/json")) {
    return response.json();
  }

  return response;
}

