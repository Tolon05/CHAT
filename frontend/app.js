document.getElementById("login-form").addEventListener("submit", async function (event) {
    event.preventDefault();

    let formData = new FormData(event.target);
    let data = {
        username: formData.get("username"),
        password: formData.get("password"),
    };

    let response = await fetch("/login", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(data),
    });

    let result = await response.json();

    if (response.ok) {
        // Handle success
        localStorage.setItem("access_token", result.access_token);
        window.location.href = "/dashboard";
    } else {
        // Handle error
        alert(result.detail);
    }
});
