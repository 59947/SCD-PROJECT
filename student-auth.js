
const loginTab = document.getElementById("loginTab");
const signupTab = document.getElementById("signupTab");

const loginForm = document.getElementById("loginForm");
const signupForm = document.getElementById("signupForm");


function showLogin() {
    loginForm.classList.remove("hidden");
    signupForm.classList.add("hidden");

    loginTab.classList.add("active");
    signupTab.classList.remove("active");
}


function showSignup() {
    signupForm.classList.remove("hidden");
    loginForm.classList.add("hidden");

    signupTab.classList.add("active");
    loginTab.classList.remove("active");
}


loginTab.addEventListener("click", showLogin);
signupTab.addEventListener("click", showSignup);


document.getElementById("openSignup").addEventListener("click", function(event) {
    event.preventDefault();
    showSignup();
});


document.getElementById("openLogin").addEventListener("click", function(event) {
    event.preventDefault();
    showLogin();
});


document.getElementById("forgotPassword").addEventListener("click", function(event) {
    event.preventDefault();
    alert("Password recovery functionality will be connected separately.");
});


// Check password confirmation before sending signup form
signupForm.addEventListener("submit", function(event) {

    const password = document.getElementById("signupPassword").value;
    const confirmPassword = document.getElementById("confirmPassword").value;

    if (password !== confirmPassword) {
        event.preventDefault();
        alert("Passwords do not match!");
    }

});
