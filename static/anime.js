document.addEventListener("DOMContentLoaded", () => {
    const select = document.getElementById("sequel");

    if (select && select.options.length > 10) {
        const searchBox = document.createElement("input");
        searchBox.type = "text";
        searchBox.className = "form-control my-2";
        searchBox.placeholder = "Search sequel...";
        select.parentNode.insertBefore(searchBox, select);

        searchBox.addEventListener("input", () => {
            const term = searchBox.value.toLowerCase();
            for (const option of select.options) {
                option.style.display = option.text.toLowerCase().includes(term) ? "" : "none";
            }
        });
    }

    // ⬇ Detail toggle logic moved here
    const detailToggleBtn = document.getElementById("toggleDetail");
    const detailControls = document.querySelectorAll(".detail-controls");
    let showDetailControls = false;

    if (detailToggleBtn) {
        detailToggleBtn.addEventListener("click", () => {
            showDetailControls = !showDetailControls;
            detailControls.forEach(el => el.classList.toggle("show", showDetailControls));
            detailToggleBtn.textContent = showDetailControls ? "❌ Hide View/Add" : "✨ Show View/Add";
        });
    }
});
