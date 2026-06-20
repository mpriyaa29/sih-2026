const uploadInput =
document.getElementById("faceUpload");

const processingCard =
document.getElementById("processingCard");

const form =
document.getElementById("victimForm");

uploadInput.addEventListener("change", function () {

    if (this.files.length > 0) {

        // Show Processing Animation
        processingCard.style.display = "block";

        // Submit after 3 seconds
        setTimeout(() => {

            form.submit();

        }, 3000);
    }
});