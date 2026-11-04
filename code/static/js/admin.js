document.addEventListener("DOMContentLoaded", function () {
    const currentPath = window.location.pathname;

    document.querySelectorAll(".eventa-menu .menu-link").forEach(link => {
        if (link.pathname === currentPath) {
            link.classList.add("active");
        }
    });
});
