// console.log("PAPERVIEW Content script running");

// select id=cshl_widget
var parentElement = document.querySelector("#cshl_widget")

// console.log("Parent element:", parentElement);
// console.log("Parent element text:", parentElement.textContent);
var link = document.createElement("a");
// console.log(window.location.href)
link.textContent = "Paperview";
link.href = "https://anaka--paperview-api-fastapi-app.modal.run/request-overview/?url=" + encodeURIComponent(window.location.href);
// console.log("Link href:", link.href);


var separator = document.createElement("span");
separator.style = "color: #000; -webkit-font-smoothing: antialiased; margin: 0; border: 0; outline: 0; vertical-align: baseline; font: inherit; border-style: solid; border-color: gray; border-top-width: 2px; border-bottom-width: 2px; padding: 0 2px; ";
parentElement.appendChild(separator);

// make the link open in a new tab
link.target = "_blank";
link.style = "color: #6c63ff; -webkit-font-smoothing: antialiased; margin: 0; border: 0; outline: 0; vertical-align: baseline; font: inherit; font-weight: 400; text-decoration: none; border-width: 2px; border-style: solid; border-color: gray; padding: 3px 5px; cursor: pointer; background-color: #fff; border-radius: 3px; border-top-color: #6c63ff; border-bottom-color: #6c63ff; border-left-color: #6c63ff; border-right-color: #6c63ff; ";
console.log("Link style:", link.style);

parentElement.appendChild(link);
