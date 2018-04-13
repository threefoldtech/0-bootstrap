var allValid = false;
var allValidReason = '';

var buildlist = ['ipxe', 'iso', 'usb', 'uefi'];
var finalUrl = '...';
var items = {
    'branch': '',
    'zerotier': '',
    'kargs': '',
};

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

function update_trigger() {
    allValid = true;

    items['branch'] = document.getElementById('branch').value;
    setValid('branch', (items['branch'] != '----'), "The selected branch is not valid");

    items['zerotier'] = document.getElementById('ztnet').value;

    if(document.getElementById('nozt').checked)
        items['zerotier'] = '0';

    setValid('ztnet', (items['zerotier'] == '0' || items['zerotier'].length == 16), "Invalid Zerotier Netork ID");

    items['kargs'] = document.getElementById('kargs').value;
    setValid('kargs', true);

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
