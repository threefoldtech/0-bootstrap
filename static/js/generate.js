var allValid = false;
var allValidReason = '';

var buildlist = ['ipxe', 'iso', 'usb', 'uefi', 'uefimg', 'krn'];
var finalUrl = '...';

var tfmodes = {"prod": "success", "test": "warning", "dev": "danger", "qa": "info"};
var tfmode = "prod";
var farmId = undefined;

function farmerid_invalid() {
    allValid = false;
    $("#farmerid").removeClass("is-valid");
    $("#farmerid").addClass("is-invalid");
    allValidReason = 'Please fix your Farmer ID';

    update_url();
}

function farmerid_valid() {
    allValid = true;
    $("#farmerid").removeClass("is-invalid");
    $("#farmerid").addClass("is-valid");

    update_url();
}

function update_trigger(initialAllValid) {
    const regex = /^\d+$/;
    const fid = $("#farmerid").val();

    if(fid === "") {
        $('#farmerid-cleared').html("Missing");
        return farmerid_invalid();
    }

    // the fid (farmer id) may only contain integers 0-9
    if(! regex.test(fid)) {
        $('#farmerid-cleared').html("Invalid");
        return farmerid_invalid();
    }

    let id = parseInt(fid)

    getFarm(id)
        .then(name => {
            if (name === "") {
                $('#farmerid-cleared').html("Non-existent");
                return farmerid_invalid();
            } else {
                $('#farmerid-cleared').html(name);
                farmId = id; // save the farm id
                return farmerid_valid();
            }
        })
        .catch(error => {
            console.error(error);
            $('#farmerid-cleared').html("error");
            return farmerid_invalid();
        });

}

async function getFarm(fid) {
    const endpoint = 'https://graphql.grid.tf/graphql';

    const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            query: `
            query MyQuery($fid: Int!) {
            farms(where: {farmID_eq: $fid }) {
                 name
                }
            }`,
            variables: { fid }
        })
    });

    const data = await response.json();
    let farms = data.data.farms
    return (farms.length === 0) ? "" : farms[0].name
}

function update_url() {
    if(!allValid) {
        // document.getElementById('userurl').innerHTML = 'Your URL is not ready yet. ' + allValidReason;
        update_urls_fails();

        $("#jumbofinal").addClass('jumbo-nok');
        $("#jumbofinal").removeClass('jumbo-ok');

        return;
    }

    $("#jumbofinal").removeClass('jumbo-nok');
    $("#jumbofinal").addClass('jumbo-ok');

    // instead of using .html to get the value, retrieve it from the var
    var userurl = '/' + tfmode + '/' + String(farmId)

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
    update_url();
}