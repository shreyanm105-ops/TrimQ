// ========================================
// TrimQ API Helper
// ========================================

const API_BASE = "http://127.0.0.1:8000";

function getToken() {
    return localStorage.getItem("trimq_token");
}

function getCurrentUser() {
    try {
        return JSON.parse(localStorage.getItem("trimq_user") || "null");
    } catch (error) {
        return null;
    }
}

async function apiRequest(endpoint, options = {}) {
    const token = getToken();

    const headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        ...(options.headers || {})
    };

    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }

    const config = {
        ...options,
        headers
    };

    try {
        const response = await fetch(`${API_BASE}${endpoint}`, config);

        let data = null;

        const contentType = response.headers.get("content-type") || "";

        if (contentType.includes("application/json")) {
            data = await response.json();
        } else {
            const text = await response.text();
            data = text ? { detail: text } : null;
        }

        if (!response.ok) {
            const message = formatApiError(data?.detail)
                || formatApiError(data?.message)
                || `Request failed with status ${response.status}`;

            throw new Error(message);
        }

        return data;

    } catch (error) {
        console.error("TrimQ API Error:", error);
        throw error;
    }
}

function formatApiError(error) {
    if (typeof error === "string") {
        return error;
    }

    if (Array.isArray(error)) {
        return error
            .map(formatApiError)
            .filter(Boolean)
            .join("; ");
    }

    if (error && typeof error === "object") {
        const message = error.msg || error.message || error.detail;
        if (typeof message === "string") {
            const location = Array.isArray(error.loc)
                ? error.loc.filter(part => !["body", "query", "path"].includes(part)).join(".")
                : "";
            return location ? `${location}: ${message}` : message;
        }
    }

    return "";
}


// ========================================
// GET
// ========================================

async function apiGet(endpoint) {
    return apiRequest(endpoint, {
        method: "GET"
    });
}


// ========================================
// POST
// ========================================

async function apiPost(endpoint, body = {}) {
    return apiRequest(endpoint, {
        method: "POST",
        body: JSON.stringify(body)
    });
}


// ========================================
// PUT
// ========================================

async function apiPut(endpoint, body = {}) {
    return apiRequest(endpoint, {
        method: "PUT",
        body: JSON.stringify(body)
    });
}


// ========================================
// PATCH
// ========================================

async function apiPatch(endpoint, body = {}) {
    return apiRequest(endpoint, {
        method: "PATCH",
        body: JSON.stringify(body)
    });
}


// ========================================
// DELETE
// ========================================

async function apiDelete(endpoint) {
    return apiRequest(endpoint, {
        method: "DELETE"
    });
}


// ========================================
// Authentication helpers
// ========================================

function saveAuth(token, user) {
    localStorage.setItem("trimq_token", token);
    localStorage.setItem("trimq_user", JSON.stringify(user));
}

function clearAuth() {
    localStorage.removeItem("trimq_token");
    localStorage.removeItem("trimq_user");
}

function isLoggedIn() {
    return !!getToken();
}

function requireLogin() {
    if (!isLoggedIn()) {
        window.location.href = "index.html";
        return false;
    }

    return true;
}

function logout() {
    clearAuth();
    window.location.href = "index.html";
}


// ========================================
// Role helpers
// ========================================

function isCustomer() {
    const user = getCurrentUser();
    return user?.role === "customer";
}

function isBarber() {
    const user = getCurrentUser();
    return user?.role === "barber";
}

function requireCustomer() {
    if (!requireLogin()) {
        return false;
    }

    if (!isCustomer()) {
        alert("Customer access required.");
        window.location.href = "../index.html";
        return false;
    }

    return true;
}

function requireBarber() {
    if (!requireLogin()) {
        return false;
    }

    if (!isBarber()) {
        alert("Barber access required.");
        window.location.href = "../index.html";
        return false;
    }

    return true;
}