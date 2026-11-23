// Get the Refresh Status button
const refreshButton = document.getElementById("refreshStatus");

// When the student clicks the button
refreshButton.addEventListener("click", function () {

    // Show a demo message
    alert(
        "Your proposal status has been refreshed!\n\n" +
        "Current Status: Under Review\n\n" +
        "Your proposal is still being reviewed by the coordinator."
    );

});