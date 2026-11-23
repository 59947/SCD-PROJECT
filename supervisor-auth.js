
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

// Switch between Login and Signup tabs
loginTab.addEventListener("click", showLogin);
signupTab.addEventListener("click", showSignup);

// Open Signup from the Login form
document.getElementById("openSignup").addEventListener("click", function(event) {
    event.preventDefault();
    showSignup();
});

// Open Login from the Signup form
document.getElementById("openLogin").addEventListener("click", function(event) {
    event.preventDefault();
    showLogin();
});

// Forgot Password placeholder
document.getElementById("forgotPassword").addEventListener("click", function(event) {
    event.preventDefault();
    alert("Forgot Password functionality will be added later.");
});

// Check whether both signup passwords match
signupForm.addEventListener("submit", function(event) {
    const password = document.getElementById("signupPassword").value;
    const confirmPassword = document.getElementById("confirmPassword").value;

    if (password !== confirmPassword) {
        event.preventDefault();
        alert("Passwords do not match!");
    }

    // If passwords match, the form is submitted to Django.
});
