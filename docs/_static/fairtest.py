#!/bin/env python3

# Fairtest v0.9.1.9015  TODO: update json
# Copyright (C) 2024-2026, Marek Gagolewski <https://www.gagolewski.com/>
# All rights reserved.

import numpy as np
import pandas as pd
import glob
import re

def process_file(filename):
    with open(filename, "r") as f:
        data = f.read()
    res = re.search(
        r"ID:\s+(.*?)-(.*?)-(.*?)-(.*)\n"
        r"Hash:\s+(.*)\n"
        r"T-start:\s+(.*)\n"
        r"T-now:\s+(.*)\n"
        r"\s+"
        r"Window titles:\n"
        r"((?s:.)*)"
        r"VSCode plugins:\n"
        r"((?s:.)*)"
        ,
        data)

    group, host, user, uid, hash, t0, t1, windows, plugins = res.groups()

    windows = [ (res.group(1), res.group(2)) for res in re.finditer(
        r"[ ]*(\d+)[ ]+([^\n]+)\n"
        ,
        windows
    ) ]

    plugins = [ (res.group(1), res.group(2)) for res in re.finditer(
        r"[ ]*(\d+)[ ]+([^\n]+)\n"
        ,
        plugins
    ) ]


    return dict(group=group, host=host, user=user, uid=uid, hash=hash,
                t0=t0, t1=t1, windows=windows, plugins=plugins)


files = [process_file(f) for f in glob.glob("*.txt")]

print("Unique hashes: %s" % ", ".join(np.unique(np.sort([f["hash"] for f in files]))))

print("Unique groups: %s" % ", ".join(np.unique(np.sort([f["group"] for f in files]))))

print("Submission count: %d" % len(files))

print("Hosts: %s" % ", ".join(np.unique(np.sort([f["host"] for f in files]))))


pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 120)

windows = pd.DataFrame([
    (int(p[0]), p[1]) for f in files for p in f["windows"]
    if
        not p[1].startswith("Terminal - ")
        and not p[1].endswith(" - Thunar")
        and not p[1].startswith("Welcome - ")
    ], columns=["time", "item"]).groupby("item").time.agg([len, min, np.mean, max]).sort_values(["len", "mean"], ascending=False)
print(repr(windows))

plugins = pd.Series([p[1] for f in files for p in f["plugins"]]).value_counts().to_frame()
print(str(plugins))
