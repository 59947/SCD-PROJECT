
const proposalForm = document.getElementById("proposalForm");
const proposalFile = document.getElementById("proposalFile");
const fileName = document.getElementById("fileName");
const draftButton = document.getElementById("draftButton");
const submitButton = document.getElementById("submitButton");
const proposalAction = document.getElementById("proposalAction");

// Check that the form exists
if (proposalForm) {

    // DISPLAY AND VALIDATE SELECTED FILE
    if (proposalFile) {
        proposalFile.addEventListener("change", function () {

            const file = this.files[0];

            if (!file) {
                fileName.textContent = "No file selected";
                return;
            }

            const allowedExtensions = ["pdf", "doc", "docx"];
            const extension = file.name.split(".").pop().toLowerCase();

            if (!allowedExtensions.includes(extension)) {
                alert("Please select a PDF, DOC, or DOCX file.");
                this.value = "";
                fileName.textContent = "No file selected";
                return;
            }

            if (file.size > 10 * 1024 * 1024) {
                alert("File size must not exceed 10 MB.");
                this.value = "";
                fileName.textContent = "No file selected";
                return;
            }

            fileName.textContent = "Selected file: " + file.name;
        });
    }

    // SAVE AS DRAFT
    if (draftButton) {
        draftButton.addEventListener("click", function () {
            proposalAction.value = "draft";
        });
    }

    // NORMAL SUBMISSION
    if (submitButton) {
        submitButton.addEventListener("click", function () {
            proposalAction.value = "submit";
        });
    }

    // DO NOT PREVENT DEFAULT FORM SUBMISSION.
    // Django must receive the POST request.

    // RESET FILE NAME
    proposalForm.addEventListener("reset", function () {
        setTimeout(function () {
            if (fileName) {
                fileName.textContent = "No file selected";
            }

            proposalAction.value = "submit";
        }, 0);
    });
}
