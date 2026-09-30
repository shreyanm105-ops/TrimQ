// ========================================
// TrimQ Authentication
// ========================================

document.addEventListener("DOMContentLoaded", () => {
    setupLoginForm();
    setupRegisterForm();
    setupLogoutButtons();
});


// ========================================
// Login
// ========================================

function setupLoginForm() {
    const form = document.getElementById("loginForm");

    if (!form) return;

    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        const emailInput = document.getElementById("email");
        const passwordInput = document.getElementById("password");

        const email = emailInput?.value.trim();
        const password = passwordInput?.value;

        if (!email || !password) {
            showAuthMessage("Please enter email and password.", true);
            return;
        }

        try {
            setAuthLoading(true);

            const data = await apiPost("/api/auth/login", {
                email,
                password
            });

            saveAuth(data.access_token, data.user);

            const role = data.user?.role;

            if (role === "barber") {
                window.location.href = "barber/dashboard.html";
            } else {
                window.location.href = "customer/dashboard.html";
            }

        } catch (error) {
            showAuthMessage(
                error.message || "Login failed. Please check your credentials.",
                true
            );
        } finally {
            setAuthLoading(false);
        }
    });
}


// ========================================
// Register
// ========================================

function setupRegisterForm() {
    const form = document.getElementById("registerForm");

    if (!form) return;

    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        const name = document.getElementById("name")?.value.trim();
        const email = document.getElementById("email")?.value.trim();
        const phone = document.getElementById("phone")?.value.trim();
        const password = document.getElementById("password")?.value;
        const role =
            document.getElementById("role")?.value ||
            document.querySelector('input[name="role"]:checked')?.value ||
            "customer";

        if (!name || !email || !password) {
            showAuthMessage("Please fill all required fields.", true);
            return;
        }

        try {
            setAuthLoading(true);

            await apiPost("/api/auth/register", {
                name,
                email,
                phone,
                password,
                role
            });

            showAuthMessage(
                "Account created successfully. Redirecting to login...",
                false
            );

            setTimeout(() => {
                window.location.href = "index.html";
            }, 1000);

        } catch (error) {
            showAuthMessage(
                error.message || "Registration failed.",
                true
            );
        } finally {
            setAuthLoading(false);
        }
    });
}


// ========================================
// Logout
// ========================================

function setupLogoutButtons() {
    document.querySelectorAll("[data-logout]").forEach((button) => {
        button.addEventListener("click", (event) => {
            event.preventDefault();

            clearAuth();
            window.location.href = "../index.html";
        });
    });
}


// ========================================
// UI helpers
// ========================================

function showAuthMessage(message, isError = false) {
    let box = document.getElementById("authMessage");

    if (!box) {
        box = document.createElement("div");
        box.id = "authMessage";

        const form =
            document.querySelector("#loginForm") ||
            document.querySelector("#registerForm");

        if (form) {
            form.prepend(box);
        } else {
            document.body.prepend(box);
        }
    }

    box.textContent = message;

    box.style.padding = "10px 12px";
    box.style.marginBottom = "14px";
    box.style.borderRadius = "8px";
    box.style.fontSize = "14px";

    if (isError) {
        box.style.background = "#fee2e2";
        box.style.color = "#991b1b";
    } else {
        box.style.background = "#dcfce7";
        box.style.color = "#166534";
    }
}


function setAuthLoading(loading) {
    const buttons = document.querySelectorAll(
        '#loginForm button[type="submit"], #registerForm button[type="submit"]'
    );

    buttons.forEach((button) => {
        button.disabled = loading;

        if (loading) {
            button.dataset.originalText = button.textContent;
            button.textContent = "Please wait...";
        } else if (button.dataset.originalText) {
            button.textContent = button.dataset.originalText;
        }
    });
}