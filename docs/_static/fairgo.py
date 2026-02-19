#!/bin/env python3

# Fairgo v0.9.1.9015
# Copyright (C) 2024-2026, Marek Gagolewski <https://www.gagolewski.com/>
# All rights reserved.

import subprocess
import uuid
import time
import os
import json
import os.path
import glob
import sys
import datetime
import signal
import hashlib
import socket
import platform
import shutil


# ##############################################################################

# # Instrukcja dla prowadzacych:
#
# Zakładamy, ze pracujemy w /home2/samba/gagolewskim/pdu  (cenaa, zogalab, ...)
#
# Tam mamy niniejszy skrypt fairgo.py oraz szablony z rozwiązaniami, np. 'zadanie1.py'.
#
#.ssh -l gagolewskim ssh.mini.pw.edu.pl
# chmod 711 /home2/samba/gagolewskim/
#
# mkdir -p /home2/samba/gagolewskim/pdu
# chmod 770 /home2/samba/gagolewskim/pdu  # wylacza prawa do zapisu dla studentow, pozwala przeglądać nauczycielom
#
# cd /home2/samba/gagolewskim/pdu
# nano fairgo.py  # edytuj info submission_files oraz gids
#
# chmod 7773  /home2/samba/gagolewskim/pdu  # wlacza prawa do zapisu, bezposrednio przed lab

# w /home2/samba/gagolewskim/pdu zapisuje sie wszystko - zrzuty ekranów, lista uruchomionych aplikacji, rozwiązania zadań studentów; permanentna inwigilacja – chcemy, żeby każdy miał równe szanse

# Windows: client must issue `net use z: \\nonus\teachers\gagolewskim\pdu`
submission_files = ["zadanie1.py"]  # TODO: EDIT, the same dir as fairgo
gids = ["A", "B"]  # TODO: EDIT - task groups


output_path = "z:\\"  # e.g., "z:\\", "/home2/samba/gagolewskim/pdu" or "/tmp" or "c:\\Users\\root\\Desktop"
intranet = ".MINI"  # ".MINI" or ".mini.pw.edu.pl"
python_executable = sys.executable


# ##############################################################################

is_windows = (platform.system() == "Windows")
if is_windows:
    # enable ANSI escape sequences:
    os.system("color")

    # disable quick edit console mode, enable CTRL+C as SIGINT:
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(
            kernel32.GetStdHandle(-10),  # STD_INPUT_HANDLE
            129 # 0x0001 ENABLE_PROCESSED_INPUT
        )
    except:
        pass

    # disable the console window close button:
    try:
        import win32gui, win32con, win32console
        hMenu = win32gui.GetSystemMenu(win32console.GetConsoleWindow(), 0)
        win32gui.DeleteMenu(hMenu, win32con.SC_CLOSE, win32con.MF_BYCOMMAND)
    except:
        pass



# ##############################################################################

lines = 0
def printe(msg, end=""):
    global lines
    if end != "": msg += end
    print(msg, file=sys.stderr, flush=True, end="")
    lines += msg.count("\n")


def s_bold(x):
    return "\033[1m"+x+"\033[0m"


def s_italic(x):
    return "\033[3m"+x+"\033[0m"


def execcmd(cmd, stoponerror=True, printerror=True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, shell=False):
    ret = subprocess.run(
        cmd, shell=shell, check=False, encoding="UTF-8",
        stderr=stderr, stdout=stdout,
        stdin=subprocess.DEVNULL,
        preexec_fn=lambda *args: signal.signal(signal.SIGINT, signal.SIG_IGN)
    )

    if ret.returncode == 0:
        return ret.stdout.strip()
    else:
        if printerror:
            printe(s_bold("Error: "))
            printe(ret.stdout.strip(), end="\n")
        if stoponerror: sys.exit(ret.returncode)
        else: return None


def printe_missing_pkg(pkg):
    printe(s_bold("Error: ")+f"The '{pkg}' Python module is missing; install with ")
    printe(s_italic(f"{python_executable} -m pip install {pkg}"), end="\n")
    #printe("If this fails, you might need to create a virtual environment first:\n")
    #printe(s_italic("python3 -m venv ~/.virtualenvs/python3-default"), end="\n")
    #printe(s_italic("source ~/.virtualenvs/python3-default/bin/activate"), end="\n")
    #printe(s_italic("echo 'export PYTHONNOUSERSITE=1' >> ~/.bashrc"), end="\n")
    #printe(s_italic("echo 'VIRTUAL_ENV_DISABLE_PROMPT=1 source ~/.virtualenvs/python3-default/bin/activate' >> ~/.bashrc"), end="\n")


def register_window_titles(windows_all, elapsed):
    if is_windows:
        for win in pywinauto_desktop.windows():
            if not win.is_visible(): continue
            wtext = win.window_text()
            if wtext in ["", "Program Manager", "Microsoft Text Input Application", "Task Manager"]: continue
            windows_all[wtext] = windows_all.get(wtext, 0)+elapsed
    else:
        # windows_cur = execcmd(["wmctrl", "-l"], stoponerror=False).split("\n")
        # for w in windows_cur:
        #     windows_all[w] = windows_all.get(w, 0)+1
        for ewmh_client in ewmh.getClientList():
            wtext = ewmh.getWmName(ewmh_client).decode("UTF-8")
            wtext = w.removeprefix("● ")  # Code - OSS - unsaved
            if wtext == "": continue
            windows_all[wtext] = windows_all.get(wtext, 0)+elapsed


def register_codeplugs(codeplugs_all, elapsed):
    if is_windows:
        pass
    else:
        # codeplugs_cur = execcmd(["code", "--list-extensions"], stderr=subprocess.DEVNULL, stoponerror=False).split("\n")
        codeplugs_cur = [os.path.basename(p) for p in glob.glob(os.path.expanduser("~/.vscode**/extensions/*")) if os.path.isdir(p)]
        for w in codeplugs_cur:
            if w != "":
                codeplugs_all[w] = codeplugs_all.get(w, 0)+elapsed


def do_chmod():
    if is_windows:
        pass
    else:
        execcmd("chmod o-rwx . *", shell=True, stoponerror=False)
        execcmd("chmod g-rwx . *", shell=True, stoponerror=False)
        execcmd("chmod -f o-rw ~ ~/Desktop", shell=True, stoponerror=False)
        execcmd("chmod -f g-rwx ~ ~/Desktop", shell=True, stoponerror=False)


def ftime(t):
    return t.isoformat(" ", "seconds")
    #return t.isoformat()


def take_screenshot(filename):
    with mss() as sct:
        sct.shot(mon=-1, output=filename)


# ##############################################################################

printe(s_bold("Fairgo:")+"    "+s_italic("Because everyone has a right for a fair go!")+"\n")
printe("           Copyright (C) 2024–2026, Prof. Marek Gagolewski\n")


try:
    from mss import mss
except ImportError:
    printe_missing_pkg("mss")
    sys.exit(1)


if is_windows:
    try:
        import pywinauto
        pywinauto_desktop = pywinauto.Desktop(backend="win32")  # "uia" is slow
    except ImportError:
        printe_missing_pkg("pywinauto")
        sys.exit(1)
else:
    try:
        from ewmh import EWMH
        ewmh = EWMH()
    except ImportError:
        printe_missing_pkg("ewmh")
        sys.exit(1)


if len(sys.argv) != 2 or sys.argv[1] not in gids:
    printe(s_bold("Error: ")+"Usage: %s %s <group>, where <group> is in %r\n" % (python_executable, sys.argv[0], gids))
    sys.exit(4)


whoami   = os.getlogin()
gid      = sys.argv[1]
uid      = str(uuid.uuid4())
t0       = datetime.datetime.now()  # timer start
t2       = None  # last window title fetch time
t3       = None  # last sync time
hostname = socket.getfqdn()  #socket.gethostname()


if output_path in ["/tmp", "c:\\Users\\root\\Desktop"]:
    printe(s_bold("Test mode: Fairgo's running in TEST MODE!"), end="\n")
else:
    if not hostname.endswith(intranet):
        printe(s_bold("Error: "))
        printe(f"This script can only be run from within {intranet}.", end="\n")
        sys.exit(4)
    hostname = hostname.removesuffix(intranet)


with open(__file__, "rb") as f:
    thishash = hashlib.file_digest(f, "sha256").hexdigest()

output_name = gid + "-" + hostname + "-" + whoami + "-" + str(int(t0.timestamp())) + "-" + uid
output_file = os.path.join(output_path, output_name)


if len(os.listdir()) > 0:
    printe(s_bold("Error: ")+"This script must be run from an empty directory.\n")
    sys.exit(3)


for f in submission_files:  # copy all template files to cwd
    shutil.copyfile(os.path.join(output_path, f), f)

# submission_files = execcmd(
#     ["tar", "-zxvf", template_path],
#     stoponerror=True
# ).split("\n")


done = False
def sigint_handler(sig, frame):
    global done  # lol
    printe(s_bold("SIGINT received... "))
    done = True


printe("\033]0;fairgo (%s-%s)\a" % (thishash[:4], output_name[:-43]))
printe("           When done, press CTRL+C to exit.\n")
printe("           \033[4mGood luck!\033[0m\n\n")

printe("Submission ID:     %s-%s\n" % (thishash[:4], output_name[:-43]))
printe("Working directory: %s\n" % (os.getcwd(), ))
printe("Start time:        %s\n" % (ftime(t0), ))


signal.signal(signal.SIGINT, sigint_handler)
windows_all = dict()
codeplugs_all = dict()
lines = 0

while not done:
    if lines > 0:
        printe(f"\033[{lines}F")
        lines = 0

    tcur = datetime.datetime.now()
    elapsed = 666 if t2 is None else ((tcur-t2).total_seconds())
    if elapsed < 0.9: time.sleep(1-elapsed-0.05)  # co za syf

    tcur = datetime.datetime.now()
    elapsed = 0 if t2 is None else ((tcur-t2).total_seconds())
    t2 = tcur
    printe("Current time:      %s\n" % (ftime(tcur), ))
    printe("\n")

    try:
        do_chmod()
    except Exception as e:
        printe(s_bold("Error: ")+"could not update file permissions.\n")

    try:
        take_screenshot(output_file+".png")
    except Exception as e:
        printe(s_bold("Error: ")+"A screenshot could not be taken.\n")

    try:
        register_window_titles(windows_all, elapsed)
    except Exception as e:
        printe(s_bold("Error: ")+"The app list could not be fetched.\n")

    try:
        register_codeplugs(codeplugs_all, elapsed)
    except Exception as e:
        printe(s_bold("Error: ")+"VSCode plugin list could not be fetched.\n")


    if done or t3 is None or (datetime.datetime.now()-t3).total_seconds() >= 4.5:
        printe("\033[0J")

        submission_data = {
            "id": output_name,
            "hash": thishash,
            "host": hostname,
            "group": gid,
            "user": whoami,
            "t_start": ftime(t0),
            "t_now": ftime(tcur),
            "windows": [(v, k) for k, v in reversed(sorted(windows_all.items(), key=lambda item: item[1]))],
            "vscode-plugins": [(v, k) for k, v in reversed(sorted(codeplugs_all.items(), key=lambda item: item[1]))],
        }

        with open(output_file+".json", "w") as f:
            json.dump(submission_data, f, indent="  ")

        try:
            # zipout = execcmd(
            #     # ["tar", "--exclude-vcs-ignores", "--exclude-vcs", "--sort=name", "-zcvf", output_file+".tar.gz", "."]
            #     ["tar", "-zcvf", output_file+".tar.gz"] + submission_files,
            #     stoponerror=False
            # )
            # if zipout is None: raise RuntimeError("tar failed")
            # zipout = zipout.split("\n")
            zipout = []
            for f in submission_files:
                shutil.copyfile(f, os.path.join(output_path, output_file+"-"+f))
                zipout.append(f)

            printe("Synced files in the current working directory:\n")
            #printe("Edit/create `.gitignore` to exclude some files.\n")
            printe("\n".join(zipout), end="\n")
            t3 = datetime.datetime.now()  # last sync time
            printe("Last sync time:    %s\n" % ftime(t3))

        except Exception as e:
            printe(s_bold("Error: ")+"Sync failed. Last sync time: %s\n" % ftime(t3))
            done = False

printe("Exiting cleanly.\n")
