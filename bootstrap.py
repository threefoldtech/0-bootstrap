import os
import shutil
import time
from flask import Flask, request, redirect, url_for, render_template, abort, Markup, make_response
from werkzeug.utils import secure_filename
from werkzeug.contrib.fixers import ProxyFix

#
# Theses location should works out-of-box if you use default settings
#
IPXE_TEMPLATE = "/opt/ipxe-template"
debug = True

app = Flask(__name__, static_url_path='/kernel')
app.url_map.strict_slashes = False

#
# Helpers
#
def ipxe_script(branch, network):
    script  = "#!ipxe\n"
    script += "dhcp\n"
    script += "chain kernel/g8os-%s-generic.efi zerotier=%s\n" % (branch, network)

    return script

#
# Routing
#
@app.route('/iso/<branch>/<network>', methods=['GET'])
def iso_branch_network(branch, network):
    return "DOWNLOAD ISO\n"

@app.route('/ipxe/<branch>/<network>', methods=['GET'])
def ipxe_branch_network(branch, network):
    script = ipxe_script(branch, network)

    response = make_response(script)
    response.headers["Content-Type"] = "plain/text"

    return response

print("[+] listening")
app.run(host="0.0.0.0", port=5555, debug=debug, threaded=True)
