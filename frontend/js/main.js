document.addEventListener("DOMContentLoaded", () => {
  fetchPlans();
  fetchReviews();
});

function fetchPlans() {
  fetch("api/plans.php")
    .then(res => res.json())
    .then(plans => {
      const container = document.getElementById("plans");
      container.innerHTML = plans.map(plan => `
        <div class="plan">
          <h3>${plan.name}</h3>
          <p>${plan.price}</p>
          <ul>${plan.features.map(f => `<li>${f}</li>`).join("")}</ul>
        </div>
      `).join("");
    });
}

function fetchReviews() {
  fetch("api/reviews.php")
    .then(res => res.json())
    .then(reviews => {
      const container = document.getElementById("reviews");
      container.innerHTML = reviews.map(r => `
        <div class="review">
          <strong>${r.name}</strong>: ${r.review} (${r.rating}/5)
        </div>
      `).join("");
    });
}

document.getElementById("reviewForm").addEventListener("submit", async function(e) {
  e.preventDefault();

  const rating = document.getElementById("rating").value;
  const comment = document.getElementById("comment").value;

  const response = await fetch("/api/reviews", {
    method: "POST",
    credentials: "include", // required for Flask sessions
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ rating: parseInt(rating), comment })
  });

  const result = await response.json();
  const messageBox = document.getElementById("reviewMessage");

  if (response.ok) {
    messageBox.innerHTML = `<span style="color: green;">${result.message}</span>`;
    document.getElementById("reviewForm").reset();
  } else {
    messageBox.innerHTML = `<span style="color: red;">${result.message}</span>`;
  }
});


