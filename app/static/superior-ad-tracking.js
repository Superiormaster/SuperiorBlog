(function () {
    "use strict";

    const SELECTOR = [
        "[data-impression-url][data-impression-event-id]"
    ].join(",");

    const VISIBILITY_THRESHOLD = 0.5;
    const REQUIRED_VISIBLE_TIME = 1000;

    function getAdData(element) {
        return {
            campaignId: element.dataset.campaignId,
            impressionUrl: element.dataset.impressionUrl,
            eventId: element.dataset.impressionEventId,
            publisher: element.dataset.publisher,
            placement: element.dataset.placement,
        };
    }

    function isValidAd(data) {
        return Boolean(
            data.campaignId &&
            data.impressionUrl &&
            data.eventId &&
            data.publisher &&
            data.placement
        );
    }

    function isElementVisible(element) {
        if (!element || !element.isConnected) {
            return false;
        }

        if (document.visibilityState !== "visible") {
            return false;
        }

        const rect = element.getBoundingClientRect();

        if (rect.width <= 0 || rect.height <= 0) {
            return false;
        }

        const viewportWidth =
            window.innerWidth || document.documentElement.clientWidth;

        const viewportHeight =
            window.innerHeight || document.documentElement.clientHeight;

        const visibleWidth = Math.max(
            0,
            Math.min(rect.right, viewportWidth) - Math.max(rect.left, 0)
        );

        const visibleHeight = Math.max(
            0,
            Math.min(rect.bottom, viewportHeight) - Math.max(rect.top, 0)
        );

        const visibleArea = visibleWidth * visibleHeight;
        const totalArea = rect.width * rect.height;

        if (totalArea <= 0) {
            return false;
        }

        return visibleArea / totalArea >= VISIBILITY_THRESHOLD;
    }

    function initializeAd(element) {
        if (element.dataset.trackingInitialized === "true") {
            return;
        }

        element.dataset.trackingInitialized = "true";

        const data = getAdData(element);

        if (!isValidAd(data)) {
            console.warn(
                "[Superior Ads] Invalid tracking data:",
                element
            );
            return;
        }

        let sent = false;
        let inFlight = false;
        let visible = false;
        let visibleTimer = null;

        function clearVisibilityTimer() {
            if (visibleTimer !== null) {
                clearTimeout(visibleTimer);
                visibleTimer = null;
            }
        }

        async function sendImpression() {
            if (sent || inFlight || !visible) {
                return;
            }

            // Confirm that the ad is still sufficiently visible.
            if (!isElementVisible(element)) {
                visible = false;
                clearVisibilityTimer();
                return;
            }

            inFlight = true;

            const payload = {
                campaign_id: Number(data.campaignId),
                event_id: data.eventId,
                publisher: data.publisher,
                placement: data.placement,
            };

            try {
                const response = await fetch(data.impressionUrl, {
                    method: "POST",
                    mode: "cors",
                    credentials: "omit",
                    keepalive: true,
                    headers: {
                        "Content-Type": "text/plain;charset=UTF-8",
                    },
                    body: JSON.stringify(payload),
                });

                if (!response.ok) {
                    throw new Error(
                        "Impression request failed: HTTP " + response.status
                    );
                }

                sent = true;

                console.info(
                    "[Superior Ads] Impression recorded:",
                    data.campaignId
                );

            } catch (error) {
                // Allow another attempt if the ad becomes visible again.
                console.warn(
                    "[Superior Ads] Impression tracking failed:",
                    error
                );

            } finally {
                inFlight = false;
            }
        }

        function startVisibilityTimer() {
            if (sent || inFlight || visibleTimer !== null) {
                return;
            }

            visibleTimer = setTimeout(function () {
                visibleTimer = null;

                if (!visible || !isElementVisible(element)) {
                    return;
                }

                sendImpression();

            }, REQUIRED_VISIBLE_TIME);
        }

        function handleVisibilityChange(isVisible) {
            visible = isVisible;

            if (!visible) {
                clearVisibilityTimer();
                return;
            }

            startVisibilityTimer();
        }

        if ("IntersectionObserver" in window) {
            const observer = new IntersectionObserver(
                function (entries) {
                    entries.forEach(function (entry) {
                        const isVisible =
                            entry.isIntersecting &&
                            entry.intersectionRatio >= VISIBILITY_THRESHOLD;

                        handleVisibilityChange(isVisible);
                    });
                },
                {
                    threshold: [0, VISIBILITY_THRESHOLD],
                }
            );

            observer.observe(element);

        } else {
            // Fallback for older browsers.
            function checkVisibility() {
                handleVisibilityChange(isElementVisible(element));
            }

            window.addEventListener("scroll", checkVisibility, {
                passive: true,
            });

            window.addEventListener("resize", checkVisibility);

            document.addEventListener(
                "visibilitychange",
                checkVisibility
            );

            checkVisibility();
        }

        // Pause impression timing when the browser tab is hidden.
        document.addEventListener("visibilitychange", function () {
            if (document.visibilityState !== "visible") {
                handleVisibilityChange(false);
            } else {
                handleVisibilityChange(isElementVisible(element));
            }
        });
    }

    function initializeAllAds() {
        document.querySelectorAll(SELECTOR).forEach(initializeAd);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initializeAllAds);
    } else {
        initializeAllAds();
    }

    // Support ads inserted dynamically after the initial page load.
    const mutationObserver = new MutationObserver(function (mutations) {
        mutations.forEach(function (mutation) {
            mutation.addedNodes.forEach(function (node) {
                if (node.nodeType !== Node.ELEMENT_NODE) {
                    return;
                }

                if (node.matches && node.matches(SELECTOR)) {
                    initializeAd(node);
                }

                if (node.querySelectorAll) {
                    node.querySelectorAll(SELECTOR).forEach(
                        initializeAd
                    );
                }
            });
        });
    });

    mutationObserver.observe(document.documentElement, {
        childList: true,
        subtree: true,
    });

})();