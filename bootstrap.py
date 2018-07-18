import os
import sys
import shutil
import time
import tempfile
import shutil
import datetime
import operator
import sqlite3
from subprocess import call
from stat import *
from flask import Flask, request, redirect, url_for, render_template, abort, Markup, make_response, send_from_directory
from werkzeug.utils import secure_filename
from werkzeug.contrib.fixers import ProxyFix
from config import config

#
# Theses location should works out-of-box if you use default settings
#
thispath = os.path.dirname(os.path.realpath(__file__))
BASEPATH = os.path.join(thispath)

app = Flask(__name__, static_url_path='/static')
app.url_map.strict_slashes = False

#
# Database
#
def db_open():
    return sqlite3.connect(config['bootstrap-db'])

def db_check():
    db = db_open()

    # sanity check
    try:
        c = db.cursor()
        c.execute("SELECT COUNT(*) FROM provision")
        db.close()

    except sqlite3.OperationalError:
        print("[-] database not initialized, please check installation steps")
        sys.exit(1)

db_check()

#
# Helpers
#
def ipxe_script(branch, network, extra=""):
    source = 'zero-os-%s.efi' % branch
    kernel = os.path.join(config['kernel-path'], source)

    if not os.path.exists(kernel):
        source = '%s.efi' % branch
        kernel = os.path.join(config['kernel-path'], source)

        if not os.path.exists(kernel):
            abort(404)

    protocol = 'https'
    if 'unsecure' in request.host:
        protocol = 'http'

    kernel = "%s://%s/kernel/%s" % (protocol, request.host, source)

    script  = "#!ipxe\n"
    script += "echo ================================\n"
    script += "echo == Zero-OS Kernel Boot Loader ==\n"
    script += "echo ================================\n"
    script += "echo \n\n"
    script += "echo Initializing network\n"
    script += "dhcp || goto failed\n\n"
    script += "echo Synchronizing time\n"
    script += "ntp pool.ntp.org || \n\n"
    script += "echo \n"
    script += "show ip\n"
    script += "route\n"
    script += "echo \n\n"
    script += "echo Downloading Zero-OS image...\n"
    script += "chain %s" % kernel

    if network and network != "null" and network != "0":
        script += " zerotier=%s" % network

    if extra:
        script += " " + extra

    script += " ||\n"
    script += "\n:failed\n"
    script += "sleep 10"

    return script

def ipxe_quick_script(branch, network, extra=""):
    source = 'zero-os-%s.efi' % branch
    kernel = os.path.join(config['kernel-path'], source)

    if not os.path.exists(kernel):
        source = '%s.efi' % branch
        kernel = os.path.join(config['kernel-path'], source)

        if not os.path.exists(kernel):
            abort(404)

    protocol = 'https'
    if 'unsecure' in request.host:
        protocol = 'http'

    kernel = "%s://%s/kernel/%s" % (protocol, request.host, source)

    script  = "#!ipxe\n"
    script += "echo Synchronizing time\n"
    script += "ntp pool.ntp.org || \n\n"
    script += "echo Downloading Zero-OS image...\n"
    script += "chain %s" % kernel

    if network and network != "null" and network != "0":
        script += " zerotier=%s" % network

    if extra:
        script += " " + extra

    script += " ||\n"
    script += "\n:failed\n"
    script += "sleep 10"

    return script

def ipxe_error(message):
    script  = "#!ipxe\n"
    script += "echo ================================\n"
    script += "echo == Zero-OS Kernel Boot Loader ==\n"
    script += "echo ================================\n"
    script += "echo \n\n"
    script += "echo Error: %s\n" % message
    script += "sleep 240"

    return script

def ipxe_provision():
    protocol = 'https'
    if 'unsecure' in request.host:
        protocol = 'http'

    script  = "#!ipxe\n"
    script += "echo =================================\n"
    script += "echo == Zero-OS Client Provisioning ==\n"
    script += "echo =================================\n"
    script += "echo \n\n"
    script += "set idx:int32 0"
    script += "\n"
    script += "echo Initializing network\n"
    script += "\n"
    script += ":loop isset ${net${idx}/mac} || goto loop_done\n"
    script += 'echo Initializing net${idx} [${net${idx}/mac}]'
    script += "\n"
    script += "ifconf --configurator dhcp net${idx} || goto loop_fail\n"
    script += "echo Synchronizing time\n"
    script += "ntp pool.ntp.org || \n\n"
    script += "echo \n"
    script += "show ip\n"
    script += "route\n"
    script += "echo \n\n"
    script += "echo Requesting provisioning configuration...\n"
    script += "chain %s://%s/provision/${net0/mac} || goto loop_fail\n" % (protocol, request.host)

    script += "\n:failed\n"
    script += "sleep 10\n\n"

    script += ":loop_fail\n"
    script += "inc idx && goto loop\n\n"

    script += ":loop_done\n"
    script += "echo No network connectivity.\n"


    return script


def text_reply(payload):
    response = make_response(payload)
    response.headers["Content-Type"] = "text/plain"

    return response

#
# Routing
#
@app.route('/kernel/<path:filename>', methods=['GET'])
def download(filename):
    print("[+] downloading: %s" % filename)
    return send_from_directory(directory=config['kernel-path'], filename=filename)

#
# Image Generator
#
@app.route('/iso/<branch>', methods=['GET'])
def iso_branch(branch):
    return iso_branch_network_extra(branch, "", "")

@app.route('/iso/<branch>/<network>', methods=['GET'])
def iso_branch_network(branch, network):
    return iso_branch_network_extra(branch, network, "")

@app.route('/iso/<branch>/<network>/<extra>', methods=['GET'])
def iso_branch_network_extra(branch, network, extra):
    print("[+] branch: %s, network: %s, extra: %s" % (branch, network, extra))

    response = make_response("Request failed")

    with tempfile.TemporaryDirectory() as tmpdir:
        src = os.path.join(tmpdir, "src")

        print("[+] copying template: %s > %s" % (config['ipxe-template'], src))
        call(["cp", "-ar", config['ipxe-template'], src])

        print("[+] creating ipxe script")
        with open(os.path.join(tmpdir, "boot.ipxe"), 'w') as f:
            f.write(ipxe_script(branch, network, extra))

        print("[+] building iso")
        script = os.path.join(BASEPATH, "scripts", "mkiso.sh")
        call(["bash", script, tmpdir])

        isocontents = ""
        with open(os.path.join(tmpdir, "ipxe.iso"), 'rb') as f:
            isocontents = f.read()

        response = make_response(isocontents)
        response.headers["Content-Type"] = "application/octet-stream"
        response.headers['Content-Disposition'] = "inline; filename=ipxe-%s.iso" % branch

    return response

@app.route('/usb/<branch>', methods=['GET'])
def usb_branch(branch):
    return usb_branch_network_extra(branch, "", "")

@app.route('/usb/<branch>/<network>', methods=['GET'])
def usb_branch_network(branch, network):
    return usb_branch_network_extra(branch, network, "")

@app.route('/usb/<branch>/<network>/<extra>', methods=['GET'])
def usb_branch_network_extra(branch, network, extra):
    print("[+] branch: %s, network: %s, extra: %s" % (branch, network, extra))

    response = make_response("Request failed")

    with tempfile.TemporaryDirectory() as tmpdir:
        src = os.path.join(tmpdir, "src")

        print("[+] copying template: %s > %s" % (config['ipxe-template'], src))
        call(["cp", "-ar", config['ipxe-template'], src])

        print("[+] creating ipxe script")
        with open(os.path.join(tmpdir, "boot.ipxe"), 'w') as f:
            f.write(ipxe_script(branch, network, extra))

        print("[+] building iso")
        script = os.path.join(BASEPATH, "scripts", "mkusb.sh")
        call(["bash", script, tmpdir])

        isocontents = ""
        with open(os.path.join(tmpdir, "ipxe.usb"), 'rb') as f:
            isocontents = f.read()

        response = make_response(isocontents)
        response.headers["Content-Type"] = "application/octet-stream"
        response.headers['Content-Disposition'] = "inline; filename=ipxe-%s.img" % branch

    return response

@app.route('/krn-generic', methods=['GET'])
def krn_generic():
    print("[+] generic ipxe kernel")

    response = make_response("Request failed")

    with tempfile.TemporaryDirectory() as tmpdir:
        src = os.path.join(tmpdir, "src")

        print("[+] copying template: %s > %s" % (config['ipxe-template'], src))
        call(["cp", "-ar", config['ipxe-template'], src])

        print("[+] building kernel")
        script = os.path.join(BASEPATH, "scripts", "mkkrn-generic.sh")
        call(["bash", script, tmpdir])

        isocontents = ""
        with open(os.path.join(tmpdir, "ipxe.lkrn"), 'rb') as f:
            isocontents = f.read()

        response = make_response(isocontents)
        response.headers["Content-Type"] = "application/octet-stream"
        response.headers['Content-Disposition'] = "inline; filename=ipxe-zero-os-generic.lkrn"

    return response

@app.route('/krn-provision', methods=['GET'])
def krn_provision():
    print("[+] provision ipxe kernel")

    response = make_response("Request failed")

    with tempfile.TemporaryDirectory() as tmpdir:
        src = os.path.join(tmpdir, "src")

        print("[+] copying template: %s > %s" % (config['ipxe-template'], src))
        call(["cp", "-ar", config['ipxe-template'], src])

        print("[+] creating ipxe script")
        with open(os.path.join(tmpdir, "boot.ipxe"), 'w') as f:
            f.write(ipxe_provision())

        print("[+] building kernel")
        script = os.path.join(BASEPATH, "scripts", "mkkrn.sh")
        call(["bash", script, tmpdir])

        isocontents = ""
        with open(os.path.join(tmpdir, "ipxe.lkrn"), 'rb') as f:
            isocontents = f.read()

        response = make_response(isocontents)
        response.headers["Content-Type"] = "application/octet-stream"
        response.headers['Content-Disposition'] = "inline; filename=ipxe-zero-os-provision.lkrn"

    return response


@app.route('/uefi-generic', methods=['GET'])
def uefi_generic():
    print("[+] generic uefi ipxe")

    response = make_response("Request failed")

    with tempfile.TemporaryDirectory() as tmpdir:
        src = os.path.join(tmpdir, "src")

        print("[+] copying template: %s > %s" % (config['ipxe-template-uefi'], src))
        call(["cp", "-ar", config['ipxe-template-uefi'], src])

        print("[+] building kernel")
        script = os.path.join(BASEPATH, "scripts", "mkuefi-generic.sh")
        call(["bash", script, tmpdir])

        isocontents = ""
        with open(os.path.join(tmpdir, "ipxe.efi"), 'rb') as f:
            isocontents = f.read()

        response = make_response(isocontents)
        response.headers["Content-Type"] = "application/octet-stream"
        response.headers['Content-Disposition'] = "inline; filename=ipxe-zero-os-generic.efi"

    return response

@app.route('/uefi-provision', methods=['GET'])
def uefi_provision():
    print("[+] provisioning uefi ipxe")

    response = make_response("Request failed")

    with tempfile.TemporaryDirectory() as tmpdir:
        src = os.path.join(tmpdir, "src")

        print("[+] copying template: %s > %s" % (config['ipxe-template-uefi'], src))
        call(["cp", "-ar", config['ipxe-template-uefi'], src])

        print("[+] creating ipxe script")
        with open(os.path.join(tmpdir, "boot.ipxe"), 'w') as f:
            f.write(ipxe_provision())

        print("[+] building kernel")
        script = os.path.join(BASEPATH, "scripts", "mkuefi.sh")
        call(["bash", script, tmpdir])

        isocontents = ""
        with open(os.path.join(tmpdir, "ipxe.efi"), 'rb') as f:
            isocontents = f.read()

        response = make_response(isocontents)
        response.headers["Content-Type"] = "application/octet-stream"
        response.headers['Content-Disposition'] = "inline; filename=ipxe-zero-os-provision.efi"

    return response


@app.route('/krn/<branch>', methods=['GET'])
def krn_branch(branch):
    return krn_branch_network_extra(branch, "", "")

@app.route('/krn/<branch>/<network>', methods=['GET'])
def krn_branch_network(branch, network):
    return krn_branch_network_extra(branch, network, "")

@app.route('/krn/<branch>/<network>/<extra>', methods=['GET'])
def krn_branch_network_extra(branch, network, extra):
    print("[+] branch: %s, network: %s, extra: %s" % (branch, network, extra))

    response = make_response("Request failed")

    with tempfile.TemporaryDirectory() as tmpdir:
        src = os.path.join(tmpdir, "src")

        print("[+] copying template: %s > %s" % (config['ipxe-template'], src))
        call(["cp", "-ar", config['ipxe-template'], src])

        print("[+] creating ipxe script")
        with open(os.path.join(tmpdir, "boot.ipxe"), 'w') as f:
            f.write(ipxe_script(branch, network, extra))

        print("[+] building iso")
        script = os.path.join(BASEPATH, "scripts", "mkkrn.sh")
        call(["bash", script, tmpdir])

        isocontents = ""
        with open(os.path.join(tmpdir, "ipxe.lkrn"), 'rb') as f:
            isocontents = f.read()

        response = make_response(isocontents)
        response.headers["Content-Type"] = "application/octet-stream"
        response.headers['Content-Disposition'] = "inline; filename=ipxe-%s.lkrn" % branch

    return response

@app.route('/uefi/<branch>', methods=['GET'])
def uefi_branch(branch):
    return uefi_branch_network_extra(branch, "", "")

@app.route('/uefi/<branch>/<network>', methods=['GET'])
def uefi_branch_network(branch, network):
    return uefi_branch_network_extra(branch, network, "")

@app.route('/uefi/<branch>/<network>/<extra>', methods=['GET'])
def uefi_branch_network_extra(branch, network, extra):
    print("[+] branch: %s, network: %s, extra: %s" % (branch, network, extra))

    response = make_response("Request failed")

    with tempfile.TemporaryDirectory() as tmpdir:
        src = os.path.join(tmpdir, "src")

        print("[+] copying template: %s > %s" % (config['ipxe-template-uefi'], src))
        call(["cp", "-ar", config['ipxe-template-uefi'], src])

        print("[+] creating ipxe script")
        with open(os.path.join(tmpdir, "boot.ipxe"), 'w') as f:
            f.write(ipxe_script(branch, network, extra))

        print("[+] building iso")
        script = os.path.join(BASEPATH, "scripts", "mkuefi.sh")
        call(["bash", script, tmpdir])

        isocontents = ""
        with open(os.path.join(tmpdir, "ipxe.efi"), 'rb') as f:
            isocontents = f.read()

        response = make_response(isocontents)
        response.headers["Content-Type"] = "application/octet-stream"
        response.headers['Content-Disposition'] = "inline; filename=ipxe-%s.efi" % branch

    return response

@app.route('/uefimg/<branch>', methods=['GET'])
def uefimg_branch(branch):
    return uefimg_branch_network_extra(branch, "", "")

@app.route('/uefimg/<branch>/<network>', methods=['GET'])
def uefimg_branch_network(branch, network):
    return uefimg_branch_network_extra(branch, network, "")

@app.route('/uefimg/<branch>/<network>/<extra>', methods=['GET'])
def uefimg_branch_network_extra(branch, network, extra):
    print("[+] branch: %s, network: %s, extra: %s" % (branch, network, extra))

    response = make_response("Request failed")

    with tempfile.TemporaryDirectory() as tmpdir:
        src = os.path.join(tmpdir, "src")

        print("[+] copying template: %s > %s" % (config['ipxe-template-uefi'], src))
        call(["cp", "-ar", config['ipxe-template-uefi'], src])

        print("[+] creating ipxe script")
        with open(os.path.join(tmpdir, "boot.ipxe"), 'w') as f:
            f.write(ipxe_script(branch, network, extra))

        print("[+] building USB image")
        script = os.path.join(BASEPATH, "scripts", "mkuefimg.sh")
        call(["bash", script, tmpdir])

        isocontents = ""
        with open(os.path.join(tmpdir, "uefimg.img"), 'rb') as f:
            isocontents = f.read()

        response = make_response(isocontents)
        response.headers["Content-Type"] = "application/octet-stream"
        response.headers['Content-Disposition'] = "inline; filename=uefiusb-%s.img" % branch

    return response


@app.route('/ipxe/<branch>', methods=['GET'])
def ipxe_branch(branch):
    return ipxe_branch_network_extra(branch, "", "")

@app.route('/ipxe/<branch>/<network>', methods=['GET'])
def ipxe_branch_network(branch, network):
    return ipxe_branch_network_extra(branch, network, "")

@app.route('/ipxe/<branch>/<network>/<extra>', methods=['GET'])
def ipxe_branch_network_extra(branch, network, extra):
    print("[+] branch: %s, network: %s, extra: %s" % (branch, network, extra))
    return text_reply(ipxe_script(branch, network, extra))

@app.route('/provision/<client>')
def provision_client(client):
    print("[+] provisioning client: %s" % client)

    db = db_open()
    t = (client,)
    c = db.cursor()

    c.execute('SELECT client, branch, zerotier, kargs FROM provision WHERE client = ?', t)
    data = c.fetchone()
    db.close()

    if data is None:
        print("[-] no client registered with this identifier")
        abort(404)

    return text_reply(ipxe_quick_script(data[1], data[2], data[3]))

#
# Helpers
#
def branches_list():
    branches = []
    target = os.listdir(config['kernel-path'])
    ordered = {}

    for filename in target:
        endpoint = os.path.join(config['kernel-path'], filename)
        stat = os.stat(endpoint, follow_symlinks=False)

        if not S_ISLNK(stat.st_mode):
            continue

        ordered[endpoint] = stat.st_mtime

    starget = sorted(ordered.items(), key=operator.itemgetter(1))
    starget.reverse()

    for endpoint in starget:
        fullpath = endpoint[0]
        updated = datetime.datetime.utcfromtimestamp(endpoint[1]).strftime('%Y-%m-%d, %H:%M:%S (UTC)')

        filename = os.path.basename(fullpath)
        link = os.readlink(fullpath)

        branch = filename[:-4]
        if branch.startswith("zero-os"):
            branch = branch[8:]

        branches.append({
            'name': filename,
            'branch': branch,
            'target': link,
            'updated': updated,
        })

    return branches

#
# Web Frontend Routing
#
@app.route('/', methods=['GET'])
def homepage():
    content = {
        'links': [],
    }

    for popular in config['popular']:
        filename = "zero-os-%s.efi" % popular
        endpoint = os.path.join(config['kernel-path'], filename)

        content['links'].append({
            'name': filename,
            'branch': popular,
            'target': os.readlink(endpoint),
            'info': config['popular-description'][popular]
        })


    return render_template("home.html", **content)

@app.route('/branches', methods=['GET'])
def branches():
    content = {
        'links': branches_list(),
    }

    return render_template("branches.html", **content)

@app.route('/images', methods=['GET'])
def kernels():
    content = {
        'files': [],
    }

    target = os.listdir(config['kernel-path'])
    ordered = {}

    for filename in target:
        endpoint = os.path.join(config['kernel-path'], filename)
        stat = os.stat(endpoint, follow_symlinks=False)
        updated = datetime.datetime.utcfromtimestamp(stat.st_mtime).strftime('%Y-%m-%d, %H:%M:%S (UTC)')

        if not S_ISREG(stat.st_mode):
            continue

        ordered[endpoint] = stat.st_mtime

    starget = sorted(ordered.items(), key=operator.itemgetter(1))
    starget.reverse()

    for endpoint in starget:
        fullpath = endpoint[0]
        filename = os.path.basename(fullpath)
        updated = datetime.datetime.utcfromtimestamp(endpoint[1]).strftime('%Y-%m-%d, %H:%M:%S (UTC)')

        content['files'].append({
            'name': filename,
            'release': filename[:-4],
            'updated': updated,
        })

    return render_template("kernels.html", **content)

@app.route('/generate', methods=['GET'])
def generate():
    sources = []

    for popular in config['popular']:
        sources.append({'branch': popular})

    sources.append({'branch': '----'})
    sources += branches_list()

    content = {
        'basebranch': '',
        'branches': sources,
        'baseurl': config['base-host'],
    }

    return render_template("generate.html", **content)

@app.route('/generate/<base>', methods=['GET'])
def generate_based(base):
    content = {
        'basebranch': base,
        'baseurl': config['base-host'],
    }
    return render_template("generate.html", **content)


@app.route('/br', methods=['GET'])
def kernel_list():
    target = os.listdir(config['kernel-path'])
    target.sort()

    content = {
        'links': [],
        'files': [],
    }

    stats = {}
    ordered = {}


    for file in target:
        endpoint = os.path.join(config['kernel-path'], file)
        stats[file] = os.stat(endpoint, follow_symlinks=False)
        ordered[file] = stats[file].st_mtime

    starget = sorted(ordered.items(), key=operator.itemgetter(1))
    starget.reverse()

    for file in starget:
        file = file[0]
        if S_ISLNK(stats[file].st_mode):
            branch = file[:-4]
            if branch.startswith("zero-os"):
                branch = branch[8:]

            content['links'].append({
                'name': file,
                'branch': branch,
                'target': os.readlink(os.path.join(config['kernel-path'], file))
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
app.run(host="0.0.0.0", port=config['http-port'], debug=config['debug'], threaded=True)
