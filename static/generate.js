var allValid = false;
var allValidReason = '';

var jwtkargs = null;
var buildlist = ['ipxe', 'iso', 'usb', 'uefi', 'krn'];
var finalUrl = '...';
var items = {
    'branch': '',
    'zerotier': '',
    'kargs': '',
};

function jwtvalidate(jwt) {
    // itsyouonline public key
    var key = "-----BEGIN PUBLIC KEY-----\n" +
              "MHYwEAYHKoZIzj0CAQYFK4EEACIDYgAES5X8XrfKdx9gYayFITc89wad4usrk0n2\n" +
              "7MjiGYvqalizeSWTHEpnd7oea9IQ8T5oJjMVH5cc0H5tFSKilFFeh//wngxIyny6\n" +
              "6+Vq5t5B0V0Ehy01+2ceEon2Y0XDkIKv\n" +
              "-----END PUBLIC KEY-----";

    var acceptField = {
        'alg': ['ES384'],
        'verifyAt': KJUR.jws.IntDate.get("0"),
        'iss': ['itsyouonline'],
    };

    var isValid = true;
    var organization = null;

    try {
        isValid = KJUR.jws.JWS.verifyJWT(jwt, key, acceptField);

        if(isValid) {
            var a = jwt.split(".");
            var uClaim = b64utos(a[1]);
            var pClaim = KJUR.jws.JWS.readSafeJSONString(uClaim);

            if(pClaim['scope'].length != 1)
                return false;

            organization = pClaim['scope'][0];
            return organization.substr(14, 1000);
        }

    } catch(ex) {
        console.log(ex);
        isValid = false;
    }

    return isValid;
}

function setValid(id, value, reason) {
    if(value) {
        document.getElementById(id).classList.remove('is-invalid');
        document.getElementById(id).classList.add('is-valid');

    } else {
        document.getElementById(id).classList.remove('is-valid');
        document.getElementById(id).classList.add('is-invalid');
        allValid = false;
        allValidReason = reason;
    }
}

function farmerid() {
    var token = document.getElementById('kargs-farmer').value;

    if((organization = jwtvalidate(token)) !== false) {
        document.getElementById('kargs-farmer-org').innerHTML = '<strong>' + organization + '</strong>';
        return true;
    }

    setValid('kargs-farmer', false, 'Invalid Farmer ID token');
    return false;
}

function update_trigger_jwt() {
    // reset any flags
    jwtkargs = null;
    setValid('kargs-farmer', true);
    document.getElementById('kargs-farmer-org').innerHTML = '';

    // if jwt is not set, nothing to do
    if(!document.getElementById('kargs-farmer').value)
        return update_trigger(true);

    // checking jwt validity
    if(farmerid()) {
        jwtkargs = 'farmer_id=' + document.getElementById('kargs-farmer').value;
        return update_trigger(true);
    }

    // call default trigger
    return update_trigger(false);
}

function update_trigger(initialAllValid) {
    allValid = (initialAllValid == undefined) ? true : initialAllValid;

    var kargs = [];

    items['branch'] = document.getElementById('branch').value;
    setValid('branch', (items['branch'] != '----'), "The selected branch is not valid");

    items['zerotier'] = document.getElementById('ztnet').value;

    if(document.getElementById('nozt').checked)
        items['zerotier'] = '0';

    setValid('ztnet', (items['zerotier'] == '0' || items['zerotier'].length == 16), "Invalid Zerotier Netork ID");

    // auto validate organization
    setValid('kargs-org', true);

    if(document.getElementById('kargs-org').value) {
        kargs.push('organization="' + document.getElementById('kargs-org').value + '"');
    }

    if(document.getElementById('development').checked)
        kargs.push("development");

    if(document.getElementById('debug').checked)
        kargs.push("debug");

    if(document.getElementById('support').checked)
        kargs.push("support");

    // append global jwt (if set)
    if(jwtkargs)
        kargs.push(jwtkargs);

    // populates extra arguments
    items['kargs'] = kargs.join(" ");

    update_url();
}

function update_url() {
    if(!allValid) {
        document.getElementById('userurl').innerHTML = 'Your URL is not ready yet. ' + allValidReason;
        update_urls_fails();

        document.getElementById("jumbofinal").classList.add('jumbo-nok');
        document.getElementById("jumbofinal").classList.remove('jumbo-ok');

        return;
    }

    document.getElementById("jumbofinal").classList.remove('jumbo-nok');
    document.getElementById("jumbofinal").classList.add('jumbo-ok');

    var userurl = '/' + items['branch'] + '/' + items['zerotier'];

    if(items['kargs'])
        userurl += '/' + items['kargs'];

    finalUrl = userurl;
    document.getElementById('userurl').innerHTML = userurl;

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
