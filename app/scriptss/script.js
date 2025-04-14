function togglePassword() {
    const passwordField = document.getElementById("password");
    const isHidden = passwordField.type === "password";

    passwordField.type = isHidden ? "text" : "password";

    document.querySelector(".icon-eye").style.display = isHidden ? "none" : "inline";
    document.querySelector(".icon-eye-off").style.display = isHidden ? "inline" : "none";
}