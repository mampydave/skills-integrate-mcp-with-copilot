document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const messageDiv = document.getElementById("message");
  const loginToggle = document.getElementById("teacher-login-toggle");
  const loginForm = document.getElementById("teacher-login-form");
  const loginMessage = document.getElementById("teacher-login-message");
  const logoutButton = document.getElementById("teacher-logout");
  const teacherStatus = document.getElementById("teacher-status");
  const signupContainer = document.getElementById("signup-container");
  let teacher = null;

  function setTeacher(username) {
    teacher = username;
    const isTeacher = Boolean(teacher);
    signupContainer.classList.toggle("hidden", !isTeacher);
    loginToggle.classList.toggle("hidden", isTeacher);
    logoutButton.classList.toggle("hidden", !isTeacher);
    teacherStatus.textContent = isTeacher ? `Signed in as ${teacher}` : "";
    teacherStatus.classList.toggle("hidden", !isTeacher);
    loginForm.classList.add("hidden");
  }

  async function loadTeacherSession() {
    let username = null;
    try {
      const response = await fetch("/auth/me");
      const session = await response.json();
      if (response.ok && session.authenticated) username = session.username;
    } catch (error) {
      console.error("Error checking teacher session:", error);
    }
    setTeacher(username);
    await fetchActivities();
  }

  loginToggle.addEventListener("click", () => {
    loginForm.classList.toggle("hidden");
    loginMessage.classList.add("hidden");
    if (!loginForm.classList.contains("hidden")) {
      document.getElementById("teacher-username").focus();
    }
  });

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(loginForm);
    loginMessage.classList.add("hidden");

    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: formData.get("username"),
          password: formData.get("password"),
        }),
      });
      const result = await response.json();
      if (!response.ok) {
        throw new Error(result.detail || "Unable to sign in");
      }

      loginForm.reset();
      setTeacher(result.username);
      await fetchActivities();
    } catch (error) {
      loginMessage.textContent = error.message || "Unable to sign in";
      loginMessage.className = "error";
    }
  });

  logoutButton.addEventListener("click", async () => {
    try {
      await fetch("/auth/logout", { method: "POST" });
    } finally {
      setTeacher(null);
      await fetchActivities();
    }
  });

  // Function to fetch activities from API
  async function fetchActivities() {
    try {
      const response = await fetch("/activities");
      if (!response.ok) throw new Error("Failed to load activities");
      const activities = await response.json();

      // Clear loading message
      activitiesList.innerHTML = "";
      activitySelect.innerHTML = '<option value="">-- Select an activity --</option>';

      // Populate activities list
      Object.entries(activities).forEach(([name, details]) => {
        const activityCard = document.createElement("div");
        activityCard.className = "activity-card";

        const spotsLeft =
          details.max_participants - details.participants.length;

        // Create participants HTML with delete icons instead of bullet points
        const participantsHTML =
          details.participants.length > 0
            ? `<div class="participants-section">
              <h5>Participants:</h5>
              <ul class="participants-list">
                ${details.participants
                  .map((email) => `<li><span class="participant-email">${email}</span>${
                    teacher
                      ? `<button class="delete-btn" data-activity="${name}" data-email="${email}" aria-label="Unregister ${email}">Remove</button>`
                      : ""
                  }</li>`)
                  .join("")}
              </ul>
            </div>`
            : `<p><em>No participants yet</em></p>`;

        activityCard.innerHTML = `
          <h4>${name}</h4>
          <p>${details.description}</p>
          <p><strong>Schedule:</strong> ${details.schedule}</p>
          <p><strong>Availability:</strong> ${spotsLeft} spots left</p>
          <div class="participants-container">
            ${participantsHTML}
          </div>
        `;

        activitiesList.appendChild(activityCard);

        // Add option to select dropdown
        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        activitySelect.appendChild(option);
      });

      // Add event listeners to delete buttons
      document.querySelectorAll(".delete-btn").forEach((button) => {
        button.addEventListener("click", handleUnregister);
      });
    } catch (error) {
      activitiesList.innerHTML =
        "<p>Failed to load activities. Please try again later.</p>";
      console.error("Error fetching activities:", error);
    }
  }

  // Handle unregister functionality
  async function handleUnregister(event) {
    const button = event.target;
    const activity = button.getAttribute("data-activity");
    const email = button.getAttribute("data-email");

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/unregister?email=${encodeURIComponent(email)}`,
        {
          method: "DELETE",
        }
      );

      const result = await response.json();

      if (response.ok) {
        messageDiv.textContent = result.message;
        messageDiv.className = "success";

        // Refresh activities list to show updated participants
        fetchActivities();
      } else {
        messageDiv.textContent = result.detail || "An error occurred";
        messageDiv.className = "error";
        if (response.status === 401) {
          setTeacher(null);
          fetchActivities();
        }
      }

      messageDiv.classList.remove("hidden");

      // Hide message after 5 seconds
      setTimeout(() => {
        messageDiv.classList.add("hidden");
      }, 5000);
    } catch (error) {
      messageDiv.textContent = "Failed to unregister. Please try again.";
      messageDiv.className = "error";
      messageDiv.classList.remove("hidden");
      console.error("Error unregistering:", error);
    }
  }

  // Handle form submission
  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!teacher) return;

    const email = document.getElementById("email").value;
    const activity = document.getElementById("activity").value;

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/signup?email=${encodeURIComponent(email)}`,
        {
          method: "POST",
        }
      );

      const result = await response.json();

      if (response.ok) {
        messageDiv.textContent = result.message;
        messageDiv.className = "success";
        signupForm.reset();

        // Refresh activities list to show updated participants
        fetchActivities();
      } else {
        messageDiv.textContent = result.detail || "An error occurred";
        messageDiv.className = "error";
        if (response.status === 401) {
          setTeacher(null);
          fetchActivities();
        }
      }

      messageDiv.classList.remove("hidden");

      // Hide message after 5 seconds
      setTimeout(() => {
        messageDiv.classList.add("hidden");
      }, 5000);
    } catch (error) {
      messageDiv.textContent = "Failed to sign up. Please try again.";
      messageDiv.className = "error";
      messageDiv.classList.remove("hidden");
      console.error("Error signing up:", error);
    }
  });

  // Initialize app
  loadTeacherSession();
});
