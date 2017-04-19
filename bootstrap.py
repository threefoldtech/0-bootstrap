import os
import shutil
import time
import tempfile
import shutil
import datetime
import operator
from subprocess import call
from stat import *
from flask import Flask, request, redirect, url_for, render_template, abort, Markup, make_response
from werkzeug.utils import secure_filename
from werkzeug.contrib.fixers import ProxyFix
from config import config

#
# Theses location should works out-of-box if you use default settings
#
thispath = os.path.dirname(os.path.realpath(__file__))
BASEPATH = os.path.join(thispath)

app = Flask(__name__, static_url_path='/g8os/kernel')
app.url_map.strict_slashes = False

#
# Helpers
#
def ipxe_script(branch, network, extra=""):
    kernel = os.path.join(config['KERNEL_PATH'], 'g8os-%s.efi' % branch)

    if not os.path.exists(kernel):
        abort(404)

    kernel = "%s/kernel/g8os-%s.efi" % (config['BASE_HOST'], branch)

    script  = "#!ipxe\n"
    script += "dhcp\n"
    script += "chain %s zerotier=%s %s\n" % (kernel, network, extra)

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

@app.route('/usb/<branch>/<network>', methods=['GET'])
def usb_branch_network(branch, network):
    print("[+] branch: %s, network: %s" % (branch, network))

    response = make_response("Request failed")

    print("[+] copying template")
    with tempfile.TemporaryDirectory() as tmpdir:
        shutil.copytree(config['IPXE_TEMPLATE'], os.path.join(tmpdir, "src"), True)

        print("[+] creating ipxe script")
        with open(os.path.join(tmpdir, "boot.ipxe"), 'w') as f:
            f.write(ipxe_script(branch, network))

        print("[+] building iso")
        script = os.path.join(BASEPATH, "scripts", "mkusb.sh")
        call(["bash", script, tmpdir])

        isocontents = ""
        with open(os.path.join(tmpdir, "ipxe.usb"), 'rb') as f:
            isocontents = f.read()

        response = make_response(isocontents)
        response.headers["Content-Type"] = "application/octet-stream"
        response.headers['Content-Disposition'] = "inline; filename=ipxe-g8os-%s.img" % branch

    return response

@app.route('/ipxe/<branch>/<network>', methods=['GET'])
def ipxe_branch_network(branch, network):
    print("[+] branch: %s, network: %s" % (branch, network))
    script = ipxe_script(branch, network)

    response = make_response(script)
    response.headers["Content-Type"] = "text/plain"

    return response

@app.route('/ipxe/<branch>/<network>/<extra>', methods=['GET'])
def ipxe_branch_network_extra(branch, network, extra):
    print("[+] branch: %s, network: %s, extra: %s" % (branch, network, extra))
    script = ipxe_script(branch, network, extra)

    response = make_response(script)
    response.headers["Content-Type"] = "text/plain"

    return response

@app.route('/', methods=['GET'])
def kernel_list():
    target = os.listdir(config['KERNEL_PATH'])
    target.sort()

    content = {
        'links': [],
        'files': [],
    }

    stats = {}
    ordered = {}


    for file in target:
        endpoint = os.path.join(config['KERNEL_PATH'], file)
        stats[file] = os.stat(endpoint, follow_symlinks=False)
        ordered[file] = stats[file].st_mtime

    starget = sorted(ordered.items(), key=operator.itemgetter(1))
    starget.reverse()

    for file in starget:
        file = file[0]
        if S_ISLNK(stats[file].st_mode):
            content['links'].append({
                'name': file,
                'target': os.readlink(os.path.join(config['KERNEL_PATH'], file))
            })

    for file in starget:
        file = file[0]
        if not S_ISLNK(stats[file].st_mode):
            date = datetime.datetime.fromtimestamp(stats[file].st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            content['files'].append({
                'size': "% 3dM" % (stats[file].st_size / (1024 * 1024)),
                'date': date,
                'name': file,
            })

    return render_template("kernel.html", **content)

print("[+] listening")
app.run(host="0.0.0.0", port=config['HTTP_PORT'], debug=config['DEBUG'], threaded=True)
