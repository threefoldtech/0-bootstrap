import sys
import click
import sqlite3
import os
import inspect

@click.group()
def provision():
    pass

def database():
    path = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
    conn = sqlite3.connect("%s/../db/bootstrap.sqlite3" % path)
    return conn

@provision.command()
@click.option('--address', required=True, help='MAC Address (xx:xx:xx:xx:xx:xx)')
@click.option('--branch', default="development", help='Kernel Version (branch)')
@click.option('--zerotier', default="c7c8172af1f387a6", help='Zerotier Network when booting')
@click.option('--options', default="development support", help="Kernel Arguments")
def add(address, branch, zerotier, options):
    if len(address) != 17:
        print("[-] invalid mac address")
        sys.exit(1)

    print("[+] client (mac address): %s" % address)
    print("[+] zero-os version     : %s" % branch)
    print("[+] zerotier network    : %s" % zerotier)
    print("[+] kernel arguments    : %s" % options)
    print("[+] ")
    print("[+] inserting into database")

    db = database()
    args = (address, branch, zerotier, options)
    stmt = db.execute('INSERT INTO provision VALUES(?, ?, ?, ?);', args)
    db.commit()

    print("[+] client added")

@provision.command()
@click.option('--address', help='MAC Address (xx:xx:xx:xx:xx:xx)')
def delete(address):
    db = database()
    args = (address,)
    stmt = db.execute("DELETE FROM provision WHERE client = ?", args)
    db.commit()

    if stmt.rowcount == 0:
        print("[-] no matching client found")
        sys.exit(1)

    print("[+] %d row deleted" % stmt.rowcount)

@provision.command()
def list():
    db = database()
    stmt = db.execute("SELECT * FROM provision")
    found = 0

    for item in stmt.fetchall():
        found += 1
        print("[+] client: %s" % item[0])
        print("[+]   version : %s" % item[1])
        print("[+]   zerotier: %s" % item[2])
        print("[+]   options : %s" % item[3])

    print("[+] clients found: %d" % found)

if __name__ == "__main__":
    provision()
