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
from werkzeug.middleware.proxy_fix import ProxyFix
from config import config

#
# Theses location should works out-of-box if you use default settings
#
thispath = os.path.dirname(os.path.realpath(__file__))
BASEPATH = os.path.join(thispath)

app = Flask(__name__, static_url_path='/static')
app.url_map.strict_slashes = False

runmodes = {
    "prod": "production (v3)",
    "test": "testing (v3)",
    "dev": "development (v3)"
}

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
def get_protocol():
    if 'unsecure' in request.host:
        return 'http'

    return 'https'

# Full cycle ipxe script
def ipxe_script(release, farmer, extra="", source=None):
    if not source:
        source = 'zero-os-development-zos-v2-generic.efi'

    kernel = os.path.join(config['kernel-path'], source)

    if release not in ["prod", "test", "dev"]:
        abort(401)

    if not os.path.exists(kernel):
        abort(404)

    kernel_secure = "%s://%s/kernel/%s" % (get_protocol(), request.host, source)
    kernel_simple = "http://unsecure.%s/kernel/%s" % (request.host, source)

    chain = "nomodeset version=v3 runmode=%s" % release

    if farmer:
        chain += " farmer_id=%s" % farmer

    if extra:
        chain += " " + extra.replace("___", "/")

    script  = "#!ipxe\n"
    script += "echo ================================\n"
    script += "echo == Zero-OS Kernel Boot Loader ==\n"
    script += "echo ================================\n"
    script += "echo \n\n"

    script += "echo Release.....: %s\n" % runmodes[release]
    script += "echo Farmer......: %s\n" % farmer
    script += "echo Parameters..: %s\n" % extra
    script += "echo \n\n"

    script += "echo Initializing network\n"
    script += "set idx:int32 0\n\n"

    script += ":loop_iface isset ${net${idx}/mac} || goto failed\n"
    script += "echo Interface: net${idx}, chipset: ${net${idx}/chip}\n"
    script += "ifconf --configurator dhcp net${idx} || goto loop_next_iface\n"
    script += "echo \n"
    script += "isset ${net${idx}/ip} && echo net${idx}/ip: ${net${idx}/ip} || goto loop_next_iface\n"
    script += "isset ${net${idx}/dns} && echo net${idx}/dns: ${net${idx}/dns} || goto loop_next_iface\n"
    script += "isset ${net${idx}/gateway} && echo net${idx}/gateway: ${net${idx}/gateway} || goto loop_next_iface\n"
    script += "echo \n"
    script += "goto loop_done\n\n"

    script += ":loop_next_iface\n"
    script += "inc idx && goto loop_iface\n\n"

    script += ":loop_done\n"

    script += "echo Synchronizing time\n"
    script += "ntp pool.ntp.org || \n\n"

    # download https, fallback to http
    script += "echo Downloading Zero-OS image...\n"
    script += "chain %s %s ||\n" % (kernel_secure, chain)
    # script += "chain %s %s ||\n" % (kernel_simple, chain)

    script += "\n:failed\n"
    script += "echo Initialization failed, rebooting in 10 seconds.\n"
    script += "sleep 10\n"

    return script

# No network setup script
# Used for provision clients which have already network setup
# by provision image
def ipxe_quick_script(release, farmer, extra=""):
    source = 'zero-os-development-zos-v2-generic.efi' % "xxxx" # FIXME: hardcode url
    kernel = os.path.join(config['kernel-path'], source)

    if release not in ["prod", "test", "dev"]:
        abort(401)

    if not os.path.exists(kernel):
        abort(404)

    kernel = "%s://%s/kernel/%s" % (get_protocol(), request.host, source)

    script  = "#!ipxe\n"
    script += "echo \n\n"

    script += "echo ==================================\n"
    script += "echo == Zero-OS Client Configuration ==\n"
    script += "echo ==================================\n"

    script += "echo \n\n"
    script += "echo Release.....: %s\n" % runmodes[release]
    script += "echo Parameters..: %s\n" % extra
    script += "echo \n\n"

    script += "echo Downloading Zero-OS image...\n"
    script += "chain %s nomodeset" % kernel

    script += " runmode=%s" % release

    if farmer:
        script += " farmer_id=%s" % farmer


    if extra:
        script += " " + extra

    script += " ||\n"
    script += "\n:failed\n"
    script += "sleep 10"

    return script

# Provisioning image requesting configuration on runtime
def ipxe_provision():
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
    script += "ifconf --configurator dhcp net${idx} || goto loop_fail\n"
    script += "echo Synchronizing time\n"
    script += "ntp pool.ntp.org || \n\n"
    script += "echo \n"
    script += "show ip\n"
    script += "route\n"
    script += "echo \n\n"
    script += "echo Requesting provisioning configuration...\n"
    script += "chain %s://%s/provision/${net${idx}/mac} || goto loop_fail\n" % (get_protocol(), request.host)

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
# Generic Image Generator
#
def srcdir_from_filename(targetfile):
    efi = ["ipxe.efi", "uefimg.img"]
    if targetfile in efi:
       return config["ipxe-template-uefi"]

    return config["ipxe-template"]

def download_mkresponse(data, filename):
    response = make_response(data)
    response.headers["Content-Type"] = "application/octet-stream"
    response.headers['Content-Disposition'] = "inline; filename=%s" % filename

    return response

def generic_image_generator(release, farmer, extra, buildscript, targetfile, filename, kernel=None):
    response = make_response("Request failed")
    srcdir = srcdir_from_filename(targetfile)

    with tempfile.TemporaryDirectory() as tmpdir:
        src = os.path.join(tmpdir, "src")

        print("[+] copying template: %s > %s" % (srcdir, src))
        call(["cp", "-ar", srcdir, src])

        print("[+] creating ipxe script")
        with open(os.path.join(tmpdir, "boot.ipxe"), 'w') as f:
            f.write(ipxe_script(release, farmer, extra, kernel))

        print("[+] building: %s" % buildscript)
        script = os.path.join(BASEPATH, "scripts", buildscript)
        call(["bash", script, tmpdir])

        filecontents = ""
        with open(os.path.join(tmpdir, targetfile), 'rb') as f:
            filecontents = f.read()

        response = download_mkresponse(filecontents, filename)

    return response

def generic_image_provision(buildscript, targetfile, filename):
    response = make_response("Request failed")
    srcdir = srcdir_from_filename(targetfile)

    with tempfile.TemporaryDirectory() as tmpdir:
        src = os.path.join(tmpdir, "src")

        print("[+] copying template: %s > %s" % (srcdir, src))
        call(["cp", "-ar", srcdir, src])

        print("[+] creating ipxe script")
        with open(os.path.join(tmpdir, "boot.ipxe"), 'w') as f:
            f.write(ipxe_provision())

        print("[+] building: %s" % buildscript)
        script = os.path.join(BASEPATH, "scripts", buildscript)
        call(["bash", script, tmpdir])

        filecontents = ""
        with open(os.path.join(tmpdir, targetfile), 'rb') as f:
            filecontents = f.read()

        response = download_mkresponse(filecontents, filename)

    return response

def generic_image_quickipxe(release, farmer, extra, buildscript, targetfile, filename):
    response = make_response("Request failed")
    srcdir = srcdir_from_filename(targetfile)

    with tempfile.TemporaryDirectory() as tmpdir:
        src = os.path.join(tmpdir, "src")

        print("[+] copying template: %s > %s" % (srcdir, src))
        call(["cp", "-ar", srcdir, src])

        print("[+] creating ipxe script")
        with open(os.path.join(tmpdir, "boot.ipxe"), 'w') as f:
            f.write(ipxe_script(release, farmer, extra))

        print("[+] building: " % buildscript)
        script = os.path.join(BASEPATH, "scripts", buildscript)
        call(["bash", script, tmpdir])

        filecontents = ""
        with open(os.path.join(tmpdir, targetfile), 'rb') as f:
            filecontents = f.read()

        response = download_mkresponse(filecontents, filename)

    return response




#
# Target Image Generator
#
@app.route('/iso/<release>', methods=['GET'])
def iso_release(release):
    return iso_release_farmer_extra(release, "", "")

@app.route('/iso/<release>/<farmer>', methods=['GET'])
def iso_release_farmer(release, farmer):
    return iso_release_farmer_extra(release, farmer, "")

@app.route('/iso/<release>/<farmer>/<extra>', methods=['GET'])
def iso_release_farmer_extra(release, farmer, extra):
    print("[+] release: %s, network: %s, extra: %s" % (release, farmer, extra))
    return generic_image_generator(release, farmer, extra, "mkiso.sh", "ipxe.iso", "ipxe-%s.iso" % release)

@app.route('/usb/<release>', methods=['GET'])
def usb_release(release):
    return usb_release_farmer_extra(release, "", "")

@app.route('/usb/<release>/<farmer>', methods=['GET'])
def usb_release_farmer(release, farmer):
    return usb_release_farmer_extra(release, farmer, "")

@app.route('/usb/<release>/<farmer>/<extra>', methods=['GET'])
def usb_release_farmer_extra(release, farmer, extra):
    print("[+] release: %s, network: %s, extra: %s" % (release, farmer, extra))
    return generic_image_generator(release, farmer, extra, "mkusb.sh", "ipxe.usb", "ipxe-%s.img" % release)


@app.route('/krn-generic', methods=['GET'])
def krn_generic():
    print("[+] generic ipxe kernel")
    return generic_image_provision("mkkrn-generic.sh", "ipxe.lkrn", "ipxe-zero-os-generic.lkrn")

@app.route('/uefi-generic', methods=['GET'])
def uefi_generic():
    print("[+] generic uefi ipxe")
    return generic_image_provision("mkuefi-generic.sh", "ipxe.efi", "ipxe-zero-os-generic.efi")


@app.route('/krn-provision', methods=['GET'])
def krn_provision():
    print("[+] provision ipxe kernel")
    return generic_image_quickipxe("mkkrn.sh", "ipxe.lkrn", "ipxe-zero-os-provision.lkrn")

@app.route('/uefi-provision', methods=['GET'])
def uefi_provision():
    print("[+] provisioning uefi ipxe")
    return generic_image_quickipxe("mkuefi.sh", "ipxe.efi", "ipxe-zero-os-provision.efi")


@app.route('/krn/<release>', methods=['GET'])
def krn_release(release):
    return krn_release_farmer_extra(release, "", "")

@app.route('/krn/<release>/<farmer>', methods=['GET'])
def krn_release_farmer(release, farmer):
    return krn_release_farmer_extra(release, farmer, "")

@app.route('/krn/<release>/<farmer>/<extra>', methods=['GET'])
def krn_release_farmer_extra(release, farmer, extra):
    print("[+] release: %s, network: %s, extra: %s" % (release, farmer, extra))
    return generic_image_generator(release, farmer, extra, "mkkrn.sh", "ipxe.lkrn", "ipxe-%s.lkrn" % release)


@app.route('/uefi/<release>', methods=['GET'])
def uefi_release(release):
    return uefi_release_farmer_extra(release, "", "")

@app.route('/uefi/<release>/<farmer>', methods=['GET'])
def uefi_release_farmer(release, farmer):
    return uefi_release_farmer_extra(release, farmer, "")

@app.route('/uefi/<release>/<farmer>/<extra>', methods=['GET'])
def uefi_release_farmer_extra(release, farmer, extra):
    print("[+] release: %s, network: %s, extra: %s" % (release, farmer, extra))
    return generic_image_generator(release, farmer, extra, "mkuefi.sh", "ipxe.efi", "ipxe-%s.efi" % release)

@app.route('/uefi/<release>/<farmer>/<extra>/<kernel>', methods=['GET'])
def uefi_release_farmer_extra_kernel(release, farmer, extra, kernel):
    print("[+] release: %s, network: %s, extra: %s [kernel: %s]" % (release, farmer, extra, kernel))
    return generic_image_generator(release, farmer, extra, "mkuefi.sh", "ipxe.efi", "ipxe-%s.efi" % release, kernel)



@app.route('/uefimg/<release>', methods=['GET'])
def uefimg_release(release):
    return uefimg_release_farmer_extra(release, "", "")

@app.route('/uefimg/<release>/<farmer>', methods=['GET'])
def uefimg_release_farmer(release, farmer):
    return uefimg_release_farmer_extra(release, farmer, "")

@app.route('/uefimg/<release>/<farmer>/<extra>', methods=['GET'])
def uefimg_release_farmer_extra(release, farmer, extra):
    print("[+] release: %s, network: %s, extra: %s" % (release, farmer, extra))
    return generic_image_generator(release, farmer, extra, "mkuefimg.sh", "uefimg.img", "uefiusb-%s.img" % release)


@app.route('/ipxe/<release>', methods=['GET'])
def ipxe_release(release):
    return ipxe_release_farmer_extra(release, "", "")

@app.route('/ipxe/<release>/<farmer>', methods=['GET'])
def ipxe_release_farmer(release, farmer):
    return ipxe_release_farmer_extra(release, farmer, "")

@app.route('/ipxe/<release>/<farmer>/<extra>', methods=['GET'])
def ipxe_release_farmer_extra(release, farmer, extra):
    print("[+] release: %s, network: %s, extra: %s" % (release, farmer, extra))
    return text_reply(ipxe_script(release, farmer, extra))

@app.route('/ipxe/<release>/<farmer>/<extra>/<kernel>', methods=['GET'])
def ipxe_release_farmer_extra_kernel(release, farmer, extra, kernel):
    print("[+] release: %s, network: %s, extra: %s [kernel: %s]" % (release, farmer, extra, kernel))
    return text_reply(ipxe_script(release, farmer, extra, kernel))



@app.route('/provision/<client>')
def provision_client(client):
    print("[+] provisioning client: %s" % client)

    db = db_open()
    t = (client,)
    c = db.cursor()

    c.execute('SELECT client, release, zerotier, kargs FROM provision WHERE client = ?', t)
    data = c.fetchone()
    db.close()

    if data is None:
        print("[-] no client registered with this identifier")
        abort(404)

    return text_reply(ipxe_quick_script(data[1], data[2], data[3]))

#
# Helpers
#
#
# Web Frontend Routing
#
@app.route('/', methods=['GET'])
def homepage():
    content = {
        "baseurl": request.base_url[:-1],
    }
    return render_template("generate.html", **content)

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
def generate_v2():
    content = {}
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
            release = file[:-4]
            if release.startswith("zero-os"):
                release = release[8:]

            content['links'].append({
                'name': file,
                'release': release,
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

@app.route('/api/kernel', methods=['POST'])
def api_kernel():
    if not request.cookies.get("token"):
        return {'status': 'error', 'message': 'token not found'}

    if request.cookies.get("token") != config['api-token']:
        return {'status': 'error', 'message': 'invalid token'}

    if 'kernel' not in request.files:
        return {'status': 'error', 'message': 'no file found'}

    file = request.files['kernel']

    if file.filename == '':
        return {'status': 'error', 'message': 'no file selected'}

    source = os.path.join(config['kernel-path'], file.filename)
    print(source)

    file.save(source)

    return {'status': 'success'}

@app.route('/api/symlink/<linkname>/<target>')
def api_symlink(linkname, target):
    if not request.cookies.get("token"):
        return {'status': 'error', 'message': 'token not found'}

    if request.cookies.get("token") != config['api-token']:
        return {'status': 'error', 'message': 'invalid token'}

    check = os.path.join(config['kernel-path'], linkname)
    if os.path.islink(check) or os.path.isfile(check):
        os.remove(check)

    now = os.getcwd()
    os.chdir(config['kernel-path'])
    os.symlink(target, linkname)
    os.chdir(now)

    return {'status': 'success'}

print("[+] listening")
app.run(host="0.0.0.0", port=config['http-port'], debug=config['debug'], threaded=True)
