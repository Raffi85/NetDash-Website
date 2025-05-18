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
