var allValid = false;
var allValidReason = '';

var jwtkargs = null;
var buildlist = ['ipxe', 'iso', 'usb', 'uefi', 'krn'];
var finalUrl = '...';

var tfmodes = {"prod": "success", "test": "warning", "dev": "danger"};
var tfmode = "prod";

function update_trigger(initialAllValid) {
    if($("#farmerid").val() == "") {
        allValid = false;
        $("#farmerid").removeClass("is-valid");
        $("#farmerid").addClass("is-invalid");
        allValidReason = 'Please set your Farmer ID';

    } else {
        allValid = true;
        $("#farmerid").removeClass("is-invalid");
        $("#farmerid").addClass("is-valid");
    }

    update_url();
}

function update_url() {
    if(!allValid) {
        document.getElementById('userurl').innerHTML = 'Your URL is not ready yet. ' + allValidReason;
        update_urls_fails();

        $("#jumbofinal").addClass('jumbo-nok');
        $("#jumbofinal").removeClass('jumbo-ok');

        return;
    }

    $("#jumbofinal").removeClass('jumbo-nok');
    $("#jumbofinal").addClass('jumbo-ok');

    var userurl = '/' + tfmode + '/' + $("#farmerid").val();

    finalUrl = userurl;
    $('#userurl').html(userurl);

    update_urls();
}

function update_urls_fails() {
    for(var x in buildlist) {
        var id = 'url_' + buildlist[x];
        document.getElementById(id).innerHTML = '...';
    }
}

function update_urls() {
    for(var x in buildlist) {
        var target = buildlist[x];
        var id = 'url_' + target;
        var url = baseurl + '/' + target + finalUrl;

        document.getElementById(id).innerHTML = url;
    }
}

function go(where) {
    window.location = baseurl + '/' + where + finalUrl;
    return false;
}


function cleanmode() {
    for(var mode in tfmodes) {
        $('#tf-runmode-' + mode + ' button').removeClass("btn-" + tfmodes[mode]);
        $('#tf-runmode-' + mode + ' button').addClass("btn-outline-" + tfmodes[mode]);
    }

    $('.tf-card-selected').removeClass("tf-card-selected");
}

function setmode(mode) {
    cleanmode();

    $('#tf-runmode-' + mode).addClass("tf-card-selected");
    $('#tf-runmode-' + mode + ' button').removeClass("btn-outline-" + tfmodes[mode]);
    $('#tf-runmode-' + mode + ' button').addClass("btn-" + tfmodes[mode]);

    tfmode = mode;
}
