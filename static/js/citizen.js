// =========================
// CITIZEN REGISTRATION
// =========================

document
.getElementById("registerForm")
.addEventListener("submit", async function(e){

    e.preventDefault();

    // =========================
    // GET FORM VALUES
    // =========================

    const citizenData = {

        name: document.getElementById("name").value,

        age: document.getElementById("age").value,

        gender: document.getElementById("gender").value,

        mobile: document.getElementById("mobile").value,

        address: document.getElementById("address").value,

        blood: document.getElementById("blood").value,

        emergencyContact: document
            .getElementById("emergencyContact").value,

        allergies: document
            .getElementById("allergies").value,

        medicalHistory: document
            .getElementById("medicalHistory").value,

        password: document
            .getElementById("password").value,

        otp: document.getElementById("otp").value

    };



    console.log("Citizen Data:", citizenData);



    // =========================
    // SEND DATA TO BACKEND
    // =========================

    try{

        const response = await fetch(
            "http://127.0.0.1:5000/register",
            {

                method: "POST",

                headers:{
                    "Content-Type":"application/json"
                },

                body: JSON.stringify(citizenData)

            }
        );



        const result = await response.json();



        // =========================
        // SUCCESS MESSAGE
        // =========================

        alert(result.message);



        // =========================
        // REDIRECT
        // =========================

        window.location.href = "login.html";



    }catch(error){

        console.error(error);

        alert("Registration Failed");

    }

});



// =========================
// OTP BUTTON
// =========================

const otpBtn = document.querySelector(".otp-btn");

otpBtn.addEventListener("click", function(){

    alert("OTP Sent Successfully");

});



// =========================
// FACE IMAGE UPLOAD
// =========================

const faceImage = document.getElementById("faceImage");

faceImage.addEventListener("change", function(){

    alert("Face Image Uploaded Successfully");

});

// =========================
// FINGERPRINT REGISTRATION
// =========================

const scanBtn =
document.getElementById("scanFingerprintBtn");

if(scanBtn){

    scanBtn.addEventListener("click", async () => {

        alert(
            "Place your finger on the sensor when prompted"
        );

        try{

            const response =
            await fetch(
                "/register-fingerprint"
            );

            const result =
            await response.json();

            if(result.success){

                document.getElementById(
                    "fingerprint_id"
                ).value = result.fingerprint_id;

                alert(
                    "Fingerprint Registered Successfully!\n\nID: "
                    + result.fingerprint_id
                );

            }

            else{

                alert(
                    "Fingerprint Registration Failed"
                );

            }

        }

        catch(error){

            console.error(error);

            alert(
                "Fingerprint Registration Failed"
            );

        }

    });

}