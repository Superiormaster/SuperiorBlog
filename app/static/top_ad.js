document.addEventListener("DOMContentLoaded", function () {

    // Sticky bottom ads
    const bottomAds = document.querySelectorAll(".sticky-ad.bottom");
    bottomAds.forEach(ad => {
        const tab = ad.querySelector(".pull-tab");
        if (!tab) return;

        let expanded = false;
        const collapsedPosition = "translateY(calc(100% - 40px))";
        const expandedPosition = "translateY(0%)";

        function expand() { ad.style.transform = expandedPosition; tab.innerHTML = "▼"; expanded = true; }
        function collapse() { ad.style.transform = collapsedPosition; tab.innerHTML = "▲"; expanded = false; }

        tab.addEventListener("click", () => expanded ? collapse() : expand());

        ad.addEventListener("touchstart", e => { ad.dataset.startY = e.touches[0].clientY; });
        ad.addEventListener("touchend", e => {
            const delta = ad.dataset.startY - e.changedTouches[0].clientY;
            if(delta > 40) expand();
            else if(delta < -40) collapse();
        });

        setTimeout(collapse, 5000);

        const footer = document.querySelector("footer");
        window.addEventListener("scroll", () => {
            if(!footer) return;
            const footerTop = footer.getBoundingClientRect().top;
            const windowHeight = window.innerHeight;
            ad.style.bottom = footerTop < windowHeight ? (windowHeight - footerTop) + "px" : "0px";
        });
    });

    // Sticky top ads
    const topAds = document.querySelectorAll(".sticky-ad.top");
    topAds.forEach(ad => {
        const tab = ad.querySelector(".pull-tab");
        if (!tab) return;

        let expanded = false;
        const collapsedPosition = "translateY(-100%)";
        const expandedPosition = "translateY(0%)";

        function expand() { ad.style.transform = expandedPosition; tab.innerHTML = "▼"; expanded = true; }
        function collapse() { ad.style.transform = collapsedPosition; tab.innerHTML = "▲"; expanded = false; }

        tab.addEventListener("click", () => expanded ? collapse() : expand());

        ad.addEventListener("touchstart", e => { ad.dataset.startY = e.touches[0].clientY; });
        ad.addEventListener("touchend", e => {
            const delta = ad.dataset.startY - e.changedTouches[0].clientY;
            if(delta > 40) expand();
            else if(delta < -40) collapse();
        });

        setTimeout(collapse, 5000);
    });
});