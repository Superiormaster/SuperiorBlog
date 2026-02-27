document.addEventListener("DOMContentLoaded", function () {

    // Select all bottom sticky ads
    const bottomAds = document.querySelectorAll(".sticky-ad.bottom");

    bottomAds.forEach(ad => {
        const tab = ad.querySelector(".pull-tab");
        if (!tab) return;

        let expanded = false;
        let startY = 0;

        const collapsedPosition = "translateY(calc(100% - 40px))"; // hidden mostly
        const expandedPosition = "translateY(0%)";                 // fully visible

        function expandAd() {
            ad.style.transform = expandedPosition;
            tab.innerHTML = "▼";
            expanded = true;
        }

        function collapseAd() {
            ad.style.transform = collapsedPosition;
            tab.innerHTML = "▲";
            expanded = false;
        }

        // Click to toggle
        tab.addEventListener("click", function () {
            expanded ? collapseAd() : expandAd();
        });

        // Swipe support
        ad.addEventListener("touchstart", function (e) {
            startY = e.touches[0].clientY;
        });

        ad.addEventListener("touchend", function (e) {
            const endY = e.changedTouches[0].clientY;
            if (startY - endY > 40) {
                expandAd(); // swipe up
            } else if (endY - startY > 40) {
                collapseAd(); // swipe down
            }
        });

        // Auto collapse after 5s
        setTimeout(collapseAd, 5000);

        // Prevent covering footer
        const footer = document.querySelector("footer");
        window.addEventListener("scroll", function () {
            if (!footer) return;

            const footerTop = footer.getBoundingClientRect().top;
            const windowHeight = window.innerHeight;

            if (footerTop < windowHeight) {
                ad.style.bottom = (windowHeight - footerTop) + "px";
            } else {
                ad.style.bottom = "0px";
            }
        });
    });

});