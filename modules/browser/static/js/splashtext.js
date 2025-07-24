 // Function to get cookie by name
 function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';')[0];
}

const username = getCookie("username");

if (username) {
    document.getElementById("splash_text").innerHTML = "Hello, " + username;
    console.log("Set splash text with username " + username);
} else {
    console.log("Username cookie not found");
    window.location.href = "/login";
}