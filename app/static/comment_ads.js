document.addEventListener("DOMContentLoaded", () => {
    const stickyAd = document.querySelector('.sticky-ad.bottom');
    const commentForm = document.getElementById('fixed-comment-form');

    if (!stickyAd || !commentForm) return;

    const collapsedPosition = 100; // in %, matches your ad translateY
    const expandedPosition = 0;    // fully visible

    // Function to update comment bottom based on ad visibility
    function updateCommentPosition() {
        // Get the ad’s current translateY
        const transform = window.getComputedStyle(stickyAd).transform;
        let translateY = 0;

        if (transform && transform !== "none") {
            // Extract translateY from matrix
            const matrix = transform.match(/matrix.*\((.+)\)/)[1].split(', ');
            // For 2D: translateY is 6th element
            translateY = parseFloat(matrix[5]);
        }

        const adHeight = stickyAd.offsetHeight;
        // If ad visible, push comment above it
        if (translateY === 0) {
            commentForm.style.bottom = `${adHeight}px`;
        } else {
            // Ad collapsed, comment at bottom
            commentForm.style.bottom = `0px`;
        }
    }

    // Initial position
    updateCommentPosition();

    // Observe ad changes (toggle / collapse)
    const observer = new MutationObserver(updateCommentPosition);
    observer.observe(stickyAd, { attributes: true, attributeFilter: ['style'] });

    // Also update periodically for safety (if ad collapses with setTimeout)
    setInterval(updateCommentPosition, 200);
});