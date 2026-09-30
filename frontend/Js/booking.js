let shopId = null;
let serviceId = null;
let shop = null;
let service = null;
let shops = [];
let services = [];
let selectedDate = "";
let selectedSlot = "";
let slotRequestId = 0;

document.addEventListener("DOMContentLoaded", initializeBookingPage);

async function initializeBookingPage() {
    if (!requireCustomer()) {
        return;
    }

    const params = new URLSearchParams(window.location.search);
    shopId = params.get("shop_id");
    serviceId = params.get("service_id");

    const dateInput = document.getElementById("bookingDate");
    const today = new Date();
    const todayString = [
        today.getFullYear(),
        String(today.getMonth() + 1).padStart(2, "0"),
        String(today.getDate()).padStart(2, "0")
    ].join("-");

    dateInput.min = todayString;
    dateInput.value = todayString;
    selectedDate = todayString;
    document.getElementById("summaryDate").textContent = formatDate(todayString);

    document.getElementById("shopSelect").addEventListener("change", () => handleShopChange());
    document.getElementById("serviceSelect").addEventListener("change", handleServiceChange);
    dateInput.addEventListener("change", handleDateChange);
    document.getElementById("confirmBtn").addEventListener("click", confirmBooking);
    document.getElementById("mobileMenu").addEventListener("click", () => {
        document.getElementById("sidebar").classList.toggle("open");
    });
    document.getElementById("logoutBtn").addEventListener("click", () => {
        clearAuth();
        window.location.href = "../index.html";
    });

    try {
        await loadShops();
        const requestedShop = shops.find(item => String(item.id) === String(shopId));
        if (requestedShop) {
            document.getElementById("shopSelect").value = String(requestedShop.id);
            await handleShopChange(serviceId);
        } else {
            shopId = null;
            serviceId = null;
            await handleShopChange();
            if (params.has("shop_id")) {
                showAlert("The selected shop is unavailable. Choose a shop to continue.", "error");
            }
        }

        document.getElementById("pageLoading").hidden = true;
        document.getElementById("bookingContent").style.display = "block";
    } catch (error) {
        document.getElementById("pageLoading").hidden = true;
        showAlert(error.message || "Unable to load booking details.", "error");
    }
}

async function loadShops() {
    const response = await apiGet("/api/customer/shops");
    shops = Array.isArray(response) ? response : response?.shops || response?.data || [];

    const select = document.getElementById("shopSelect");
    select.replaceChildren(new Option("Choose a barber shop", ""));

    shops.forEach(item => {
        select.add(new Option(item.name || `Shop #${item.id}`, String(item.id)));
    });

    if (shops.length === 0) {
        select.disabled = true;
        showAlert("No barber shops are available right now.", "error");
    }
}

async function handleShopChange(preferredServiceId = "") {
    shopId = document.getElementById("shopSelect").value || null;
    const requestedShopId = shopId;
    slotRequestId += 1;
    shop = shops.find(item => String(item.id) === String(shopId)) || null;
    serviceId = null;
    service = null;
    services = [];
    selectedSlot = "";

    document.getElementById("summaryShop").textContent = shop?.name || "-";
    document.getElementById("summaryService").textContent = "Not selected";
    document.getElementById("summaryPrice").textContent = "-";
    document.getElementById("summaryDuration").textContent = "-";
    document.getElementById("summaryTime").textContent = "Not selected";

    const serviceSelect = document.getElementById("serviceSelect");
    serviceSelect.replaceChildren(new Option(
        shopId ? "Loading services..." : "Select a shop first",
        ""
    ));
    serviceSelect.disabled = true;
    updateConfirmButton();

    if (!shopId) {
        document.getElementById("slotsContainer").innerHTML =
            '<div class="slot-empty">Select a shop to see available slots.</div>';
        document.getElementById("slotHint").textContent = "Select a shop";
        return;
    }

    let response;
    try {
        response = await apiGet(
            `/api/customer/shops/${encodeURIComponent(requestedShopId)}/services`
        );
    } catch (error) {
        if (requestedShopId !== shopId) {
            return;
        }

        serviceSelect.replaceChildren(new Option("Unable to load services", ""));
        document.getElementById("slotsContainer").innerHTML =
            '<div class="slot-empty">Unable to load services for this shop.</div>';
        document.getElementById("slotHint").textContent = "Unavailable";
        showAlert(error.message || "Unable to load services.", "error");
        return;
    }

    if (requestedShopId !== shopId) {
        return;
    }

    services = (Array.isArray(response) ? response : response?.services || response?.data || [])
        .filter(item => item.is_active !== false);

    serviceSelect.replaceChildren(new Option("Choose a service", ""));
    services.forEach(item => {
        serviceSelect.add(new Option(
            `${item.name} - ₹${item.price ?? 0}`,
            String(item.id)
        ));
    });
    serviceSelect.disabled = services.length === 0;

    if (services.length === 0) {
        serviceSelect.replaceChildren(new Option("No services available", ""));
        showAlert("This shop has no services available.", "error");
    } else if (preferredServiceId && services.some(item => String(item.id) === String(preferredServiceId))) {
        serviceSelect.value = String(preferredServiceId);
        handleServiceChange();
    }

    await loadSlots(selectedDate);
}

function handleServiceChange() {
    serviceId = document.getElementById("serviceSelect").value || null;
    service = services.find(item => String(item.id) === String(serviceId)) || null;

    document.getElementById("summaryService").textContent = service?.name || "Not selected";
    document.getElementById("summaryPrice").textContent = service
        ? `₹${service.price ?? 0}`
        : "-";
    document.getElementById("summaryDuration").textContent = service?.duration_minutes
        ? `${service.duration_minutes} min`
        : "-";
    updateConfirmButton();
}

async function handleDateChange(event) {
    selectedDate = event.target.value;
    selectedSlot = "";
    document.getElementById("summaryDate").textContent = selectedDate
        ? formatDate(selectedDate)
        : "-";
    document.getElementById("summaryTime").textContent = "Not selected";
    updateConfirmButton();

    if (!selectedDate) {
        document.getElementById("slotsContainer").innerHTML =
            '<div class="slot-empty">Select a date to see available slots.</div>';
        document.getElementById("slotHint").textContent = "Select a date";
        return;
    }

    await loadSlots(selectedDate);
}

async function loadSlots(date) {
    const requestId = ++slotRequestId;
    const container = document.getElementById("slotsContainer");

    if (!shopId) {
        container.innerHTML = '<div class="slot-empty">Select a shop to see available slots.</div>';
        document.getElementById("slotHint").textContent = "Select a shop";
        updateConfirmButton();
        return;
    }

    container.innerHTML = '<div class="slot-loading">Loading available slots...</div>';
    document.getElementById("slotHint").textContent = "Loading...";

    try {
        const response = await apiGet(
            `/api/customer/shops/${encodeURIComponent(shopId)}/slots?booking_date=${encodeURIComponent(date)}`
        );

        if (requestId !== slotRequestId || date !== selectedDate) {
            return;
        }

        const slots = response?.available_slots || response?.slots || response?.data || [];
        renderSlots(slots);
    } catch (error) {
        if (requestId !== slotRequestId) {
            return;
        }

        container.innerHTML = '<div class="slot-empty">Unable to load available slots.</div>';
        document.getElementById("slotHint").textContent = "Unavailable";
        showAlert(error.message || "Unable to load available slots.", "error");
        updateConfirmButton();
    }
}

function renderSlots(slots) {
    const container = document.getElementById("slotsContainer");
    container.replaceChildren();

    if (!Array.isArray(slots) || slots.length === 0) {
        container.innerHTML = '<div class="slot-empty">No slots available for this date.</div>';
        document.getElementById("slotHint").textContent = "No slots available";
        selectedSlot = "";
        updateConfirmButton();
        return;
    }

    const grid = document.createElement("div");
    grid.className = "slots";

    slots.forEach(slot => {
        const time = typeof slot === "string"
            ? slot
            : slot?.time || slot?.slot_time || slot?.slot || "";
        if (!time) {
            return;
        }

        const button = document.createElement("button");
        button.type = "button";
        button.className = "slot-btn";
        button.textContent = formatTime(time);
        button.setAttribute("aria-pressed", "false");

        if (slot && typeof slot === "object" && (slot.available === false || slot.is_available === false)) {
            button.classList.add("disabled");
            button.disabled = true;
        } else {
            button.addEventListener("click", () => selectSlot(time, button));
        }

        grid.appendChild(button);
    });

    if (grid.childElementCount === 0) {
        container.innerHTML = '<div class="slot-empty">No slots available for this date.</div>';
        document.getElementById("slotHint").textContent = "No slots available";
        selectedSlot = "";
    } else {
        container.appendChild(grid);
        document.getElementById("slotHint").textContent = `${grid.childElementCount} slots available`;
    }

    updateConfirmButton();
}

function selectSlot(time, button) {
    selectedSlot = time;
    document.querySelectorAll("#slotsContainer .slot-btn").forEach(slotButton => {
        slotButton.classList.remove("selected");
        slotButton.setAttribute("aria-pressed", "false");
    });
    button.classList.add("selected");
    button.setAttribute("aria-pressed", "true");
    document.getElementById("summaryTime").textContent = formatTime(time);
    hideAlert();
    updateConfirmButton();
}

async function confirmBooking() {
    if (!shopId || !service || !selectedDate || !selectedSlot) {
        showAlert("Please select an available time slot.", "error");
        return;
    }

    const button = document.getElementById("confirmBtn");
    button.disabled = true;
    button.textContent = "Confirming...";
    hideAlert();

    try {
        await apiPost("/api/customer/bookings", {
            shop_id: Number(shopId),
            service_id: Number(service.id),
            booking_date: selectedDate,
            slot_time: selectedSlot
        });

        document.getElementById("successMessage").textContent =
            `Your ${service.name} at ${shop.name} is booked for ${formatDate(selectedDate)} at ${formatTime(selectedSlot)}.`;
        document.getElementById("bookingContent").style.display = "none";
        document.getElementById("successContent").style.display = "block";
    } catch (error) {
        showAlert(error.message || "This slot is no longer available. Please choose another slot.", "error");
        selectedSlot = "";
        document.getElementById("summaryTime").textContent = "Not selected";
        await loadSlots(selectedDate);
    } finally {
        button.textContent = "Confirm Booking";
        updateConfirmButton();
    }
}

function updateConfirmButton() {
    document.getElementById("confirmBtn").disabled =
    !(shopId && serviceId && service && selectedDate && selectedSlot);
}

function formatDate(dateString) {
    const date = new Date(`${dateString}T00:00:00`);
    if (Number.isNaN(date.getTime())) {
        return dateString;
    }

    return date.toLocaleDateString("en-IN", {
        day: "2-digit",
        month: "short",
        year: "numeric"
    });
}

function formatTime(timeString) {
    const parts = String(timeString).split(":");
    if (parts.length < 2) {
        return timeString;
    }

    let hours = Number.parseInt(parts[0], 10);
    if (Number.isNaN(hours)) {
        return timeString;
    }

    const period = hours >= 12 ? "PM" : "AM";
    hours = hours % 12 || 12;
    return `${hours}:${parts[1]} ${period}`;
}

function showAlert(message, type) {
    const alertBox = document.getElementById("alertBox");
    alertBox.className = `alert ${type}`;
    alertBox.textContent = message;
}

function hideAlert() {
    const alertBox = document.getElementById("alertBox");
    alertBox.className = "alert";
    alertBox.textContent = "";
}