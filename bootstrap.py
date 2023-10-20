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
        source = 'net/%s.efi' % release

    kernel = os.path.join(config['kernel-path'], source)

    if release not in config['runmodes'].keys():
        abort(401)

    if not os.path.exists(kernel):
        abort(404)

    kernel_secure = "%s://%s/kernel/%s" % (get_protocol(), request.host, source)
    kernel_simple = "http://unsecure.%s/kernel/%s" % (request.host, source)

    chain = "nomodeset version=v3 runmode=%s panic=7200" % release

    if farmer:
        chain += " farmer_id=%s" % farmer

    if extra:
        chain += " " + extra.replace("___", "/")


    settings = {
        "release": config['runmodes'][release],
        "farmerid": farmer,
        "parameters": extra,
        "kernel": kernel_secure,
        "cmdline": chain,
    }

    return render_template("boot.ipxe", **settings)

# Debug cycle ipxe script
def ipxe_debug_script(release, farmer, extra="", source=None):
    if not source:
        source = 'net/%s.efi' % release

    kernel = os.path.join(config['kernel-path'], source)

    if release not in config['runmodes'].keys():
        abort(401)

    if not os.path.exists(kernel):
        abort(404)

    kernel_secure = "%s://%s/kernel/%s" % (get_protocol(), request.host, source)
    kernel_simple = "http://unsecure.%s/kernel/%s" % (request.host, source)

    chain = "nomodeset version=v3 runmode=%s panic=7200" % release

    if farmer:
        chain += " farmer_id=%s" % farmer

    if extra:
        chain += " " + extra.replace("___", "/")

    settings = {
        "release": config['runmodes'][release],
        "farmerid": farmer,
        "parameters": extra,
        "kernel": kernel_secure,
        "cmdline": chain,
    }

    return render_template("debug.ipxe", **settings)


# No network setup script
# Used for provision clients which have already network setup
# by provision image
def ipxe_quick_script(release, farmer, extra=""):
    source = 'zero-os-development-zos-v2-generic.efi'
    kernel = os.path.join(config['kernel-path'], source)

    if release not in config['runmodes'].keys():
        abort(401)

    if not os.path.exists(kernel):
        abort(404)

    kernel = "%s://%s/kernel/%s" % (get_protocol(), request.host, source)
    cmdline = "nomodeset runmode=%s" % release

    if farmer:
        cmdline += " farmer_id=%s" % farmer

    if extra:
        cmdline += " " + extra

    settings = {
        "release": config['runmodes'][release],
        "parameters": extra,
        "kernel": kernel,
        "cmdline": cmdline,
    }

    return render_template("boot-quick.ipxe", **settings)

# Provisioning image requesting configuration on runtime
def ipxe_provision():
    url = "%s://%s/provision/${net${idx}/mac}" % (get_protocol(), request.host)
    settings = {
        "url": url,
    }

    return render_template("boot-provision.ipxe", **settings)


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

@app.route('/kernel/net/<path:filename>', methods=['GET'])
def download_net(filename):
    print("[+] downloading (network based): %s" % filename)
    return send_from_directory(directory=config['kernel-net-path'], filename=filename)

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

def generic_debug_image_generator(release, farmer, extra, buildscript, targetfile, filename, kernel=None):
    response = make_response("Request failed")
    srcdir = srcdir_from_filename(targetfile)

    with tempfile.TemporaryDirectory() as tmpdir:
        src = os.path.join(tmpdir, "src")

        print("[+] copying template: %s > %s" % (srcdir, src))
        call(["cp", "-ar", srcdir, src])

        print("[+] creating ipxe debug script")
        with open(os.path.join(tmpdir, "boot.ipxe"), 'w') as f:
            f.write(ipxe_debug_script(release, farmer, extra, kernel))

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

def baseurl():
    base = request.base_url[:-1]
    base = base.replace("http://", "https://") # force https

    return base

def kernel_list():
    files = []

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

        files.append({
            'name': filename,
            'release': filename[:-4],
            'updated': updated,
        })

    return files


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

@app.route('/iso/<release>/<farmer>/<extra>/<kernel>', methods=['GET'])
def iso_release_farmer_extra_kernel(release, farmer, extra, kernel):
    print("[+] release: %s, network: %s, extra: %s [kernel: %s]" % (release, farmer, extra, kernel))
    return generic_image_generator(release, farmer, extra, "mkiso.sh", "ipxe.iso", "ipxe-%s.iso" % release, kernel)


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

@app.route('/usb/<release>/<farmer>/<extra>/<kernel>', methods=['GET'])
def usb_release_farmer_extra_kernel(release, farmer, extra, kernel):
    print("[+] release: %s, network: %s, extra: %s [kernel: %s]" % (release, farmer, extra, kernel))
    return generic_image_generator(release, farmer, extra, "mkusb.sh", "ipxe.usb", "ipxe-%s.img" % release, kernel)



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



@app.route('/snponly/<release>/<farmer>/<extra>', methods=['GET'])
def snponly_release_farmer_extra(release, farmer, extra):
    print("[+] snponly, release: %s, network: %s, extra: %s" % (release, farmer, extra))
    return generic_image_generator(release, farmer, extra, "mksnponly.sh", "ipxe.efi", "ipxe-snp-%s.efi" % release)




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

@app.route('/uefimg/<release>/<farmer>/<extra>/<kernel>', methods=['GET'])
def uefimg_release_farmer_extra_kernel(release, farmer, extra, kernel):
    print("[+] release: %s, network: %s, extra: %s [kernel: %s]" % (release, farmer, extra, kernel))
    return generic_image_generator(release, farmer, extra, "mkuefimg.sh", "uefimg.img", "uefiusb-%s.img" % release, kernel)



@app.route('/debug/<release>/<farmer>', methods=['GET'])
def uefimg_debug_release(release, farmer):
    return generic_debug_image_generator(release, farmer, "", "mkuefimg.sh", "uefimg.img", "uefiusb-debug.img")



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
        "baseurl": baseurl(),
    }

    return render_template("generate.html", **content)

@app.route('/images', methods=['GET'])
def kernels():
    content = {
        'files': kernel_list(),
    }

    return render_template("kernels.html", **content)

@app.route('/generate', methods=['GET'])
def generate():
    content = {
        "baseurl": baseurl(),
    }

    return render_template("generate.html", **content)


    return render_template("generate.html", **content)

@app.route('/expert', methods=['GET'])
def expert():
    content = {
        "baseurl": baseurl(),
        "kernels": kernel_list()
    }

    return render_template("expert.html", **content)

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
