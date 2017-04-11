import os
import shutil
import time
import tempfile
import shutil
from subprocess import call
from flask import Flask, request, redirect, url_for, render_template, abort, Markup, make_response
from werkzeug.utils import secure_filename
from werkzeug.contrib.fixers import ProxyFix
from config import config

#
# Theses location should works out-of-box if you use default settings
#
thispath = os.path.dirname(os.path.realpath(__file__))
BASEPATH = os.path.join(thispath)

app = Flask(__name__, static_url_path='/kernel')
app.url_map.strict_slashes = False

#
# Helpers
#
def ipxe_script(branch, network):
    kernel = "%s/kernel/g8os-%s-generic.efi" % (config['BASE_HOST'], branch)

    script  = "#!ipxe\n"
    script += "dhcp\n"
    script += "chain %s zerotier=%s\n" % (kernel, network)

    return script

#
# Routing
#
@app.route('/iso/<branch>/<network>', methods=['GET'])
def iso_branch_network(branch, network):
    print("[+] branch: %s, network: %s" % (branch, network))

    response = make_response("Request failed")

    print("[+] copying template")
    with tempfile.TemporaryDirectory() as tmpdir:
        shutil.copytree(config['IPXE_TEMPLATE'], os.path.join(tmpdir, "src"), True)

        print("[+] creating ipxe script")
        with open(os.path.join(tmpdir, "boot.ipxe"), 'w') as f:
            f.write(ipxe_script(branch, network))

        print("[+] building iso")
        script = os.path.join(BASEPATH, "scripts", "mkiso.sh")
        call(["bash", script, tmpdir])

        isocontents = ""
        with open(os.path.join(tmpdir, "ipxe.iso"), 'rb') as f:
            isocontents = f.read()

        response = make_response(isocontents)
        response.headers["Content-Type"] = "application/octet-stream"
        response.headers['Content-Disposition'] = "inline; filename=ipxe-g8os-%s.iso" % branch

    return response

@app.route('/ipxe/<branch>/<network>', methods=['GET'])
def ipxe_branch_network(branch, network):
    print("[+] branch: %s, network: %s" % (branch, network))
    script = ipxe_script(branch, network)

    response = make_response(script)
    response.headers["Content-Type"] = "plain/text"

    return response

print("[+] listening")
app.run(host="0.0.0.0", port=config['HTTP_PORT'], debug=config['DEBUG'], threaded=True)
