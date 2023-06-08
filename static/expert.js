var target = "/";

function generate() {
    if(document.getElementById("farmerid").value == "") {
        $("#farmerid").addClass("is-invalid");
        $("#farmerid").focus();
        return false;
    }

    target = "/";

    target += $("#format").val() + "/";
    target += $("#network").val() + "/";
    target += $("#farmerid").val();

    if($("#kernel").val() != "default") {
        if($("#kargs").val() == "") {
            target += "/debug/" + $("#kernel").val();

        } else {
            target += "/" + $("#kargs").val() + "/" + $("#kernel").val();
        }

    } else {
        if($("#kargs").val() != "") {
            target += "/" + $("#kargs").val();
        }
    }

    $("#target").html("Target: " + target);
    $("#downbtn").removeAttr("disabled");

    return false;
}

function download() {
    console.log(target);
    window.location.href = target;

    return false;
}
