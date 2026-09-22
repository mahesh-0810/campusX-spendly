// main.js — students will add JavaScript here as features are built

// "See how it works" video modal (landing page)
(function () {
    var YOUTUBE_VIDEO_ID = "dQw4w9WgXcQ"; // placeholder — replace with real video ID

    var trigger = document.getElementById("how-it-works-btn");
    var overlay = document.getElementById("how-it-works-modal");
    var closeBtn = document.getElementById("how-it-works-modal-close");
    var iframe = document.getElementById("how-it-works-modal-iframe");

    if (!trigger || !overlay || !closeBtn || !iframe) {
        return;
    }

    function openModal(event) {
        event.preventDefault();
        iframe.src = "https://www.youtube.com/embed/" + YOUTUBE_VIDEO_ID + "?autoplay=1";
        overlay.hidden = false;
    }

    function closeModal() {
        overlay.hidden = true;
        iframe.src = ""; // stops playback
    }

    trigger.addEventListener("click", openModal);
    closeBtn.addEventListener("click", closeModal);

    overlay.addEventListener("click", function (event) {
        if (event.target === overlay) {
            closeModal();
        }
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape" && !overlay.hidden) {
            closeModal();
        }
    });
})();
