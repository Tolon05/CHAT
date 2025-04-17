// document.getElementById("login-form").addEventListener("submit", async function (event) {
//     event.preventDefault();

//     let formData = new FormData(event.target);
//     let data = {
//         username: formData.get("username"),
//         password: formData.get("password"),
//     };

//     let response = await fetch("/login", {
//         method: "POST",
//         headers: {
//             "Content-Type": "application/json",
//         },
//         body: JSON.stringify(data),
//     });

//     let result = await response.json();

//     if (response.ok) {
//         // Handle success
//         localStorage.setItem("access_token", result.access_token);
//         window.location.href = "/dashboard";
//     } else {
//         // Handle error
//         alert(result.detail);
//     }
// });


function togglePassword(inputId) {
    const input = document.getElementById(inputId);
    const toggle = input.nextElementSibling; // span.toggle-password

    if (input.type === "password") {
        input.type = "text";
    } else {
        input.type = "password";
    }

    const eye = toggle.querySelector('.icon-eye');
    const eyeOff = toggle.querySelector('.icon-eye-off');
    eye.classList.toggle('hidden');
    eyeOff.classList.toggle('hidden');
}
