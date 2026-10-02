#!/usr/bin/env python3
"""KodEdit Worker — ZIP Flat.

Ambil fail dari repo yang telah di-clone, flatten (pilihan), pecah kepada
ZIP kecil (N fail setiap satu), kemudian bungkus semua ZIP kecil ke dalam
satu ZIP besar (dipecah automatik jika melebihi had saiz Release GitHub).
"""
import argparse
import os
import re
import sys
import zipfile

HAD_RELEASE = 1900 * 1024 * 1024  # GitHub: maks 2GB setiap fail Release


def senarai_fail(akar, sub, tapis):
    base = os.path.normpath(os.path.join(akar, sub)) if sub else akar
    if not os.path.isdir(base):
        sys.exit(f"Folder '{sub}' tidak dijumpai dalam repo")
    hasil = []
    for root, dirs, files in os.walk(base):
        dirs[:] = sorted(d for d in dirs if d != ".git")
        for f in sorted(files):
            full = os.path.join(root, f)
            if os.path.islink(full) or not os.path.isfile(full):
                continue
            rel = os.path.relpath(full, base).replace(os.sep, "/")
            if tapis and tapis.lower() not in rel.lower():
                continue
            hasil.append((rel, full))
    return hasil


def nama_flat(paths):
    used = {"_peta_fail.txt"}
    out = []
    for p in paths:
        nm = p.split("/")[-1]
        if nm.lower() not in used:
            used.add(nm.lower())
            out.append(nm)
            continue
        di = nm.rfind(".")
        b, e = (nm[:di], nm[di:]) if di > 0 else (nm, "")
        k = 2
        while f"{b} ({k}){e}".lower() in used:
            k += 1
        cand = f"{b} ({k}){e}"
        used.add(cand.lower())
        out.append(cand)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--label", default="")
    ap.add_argument("--sub", default="")
    ap.add_argument("--filter", default="")
    ap.add_argument("--flat", default="true")
    ap.add_argument("--per-zip", type=int, default=10)
    a = ap.parse_args()

    flat = a.flat.lower() in ("1", "true", "ya", "yes")
    sub = a.sub.strip().strip("/")
    if ".." in sub.split("/"):
        sys.exit("Laluan sub tidak sah")
    fail = senarai_fail(a.src, sub, a.filter.strip())
    if not fail:
        sys.exit("Tiada fail dijumpai (semak folder / tapisan)")

    paths = [r for r, _ in fail]
    names = nama_flat(paths) if flat else paths
    asas = re.sub(r"[^\w.\-]+", "_", a.name) + ("-flat" if flat else "")
    os.makedirs(a.out, exist_ok=True)
    kerja = os.path.join(a.out, "_bahagian")
    os.makedirs(kerja, exist_ok=True)

    peta = "\n".join(f"{n}  ←  {p}" for n, p in zip(names, paths))
    peta_txt = f"Sumber: {a.label}\nJumlah: {len(fail)} fail\n\n{peta}\n"

    # 1) ZIP kecil
    per = a.per_zip if a.per_zip > 0 else len(fail)
    jum_bhg = (len(fail) + per - 1) // per
    lebar = len(str(jum_bhg))
    kecil = []
    for b in range(jum_bhg):
        nama = f"{asas}-bahagian{str(b + 1).zfill(lebar)}.zip" if jum_bhg > 1 else f"{asas}.zip"
        laluan = os.path.join(kerja, nama)
        with zipfile.ZipFile(laluan, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            for i in range(b * per, min((b + 1) * per, len(fail))):
                z.write(fail[i][1], names[i])
        kecil.append(laluan)

    # 2) Bungkus ke ZIP besar (pecah jika > had Release)
    besar, set_no, saiz, zf = [], 0, 0, None

    def buka_baru():
        nonlocal set_no, saiz, zf
        if zf:
            zf.close()
        set_no += 1
        laluan = os.path.join(a.out, f"{asas}-set{set_no}.zip")
        besar.append(laluan)
        zf = zipfile.ZipFile(laluan, "w", zipfile.ZIP_STORED)
        saiz = 0

    buka_baru()
    zf.writestr("_PETA_FAIL.txt", peta_txt)
    for k in kecil:
        s = os.path.getsize(k)
        if saiz > 0 and saiz + s > HAD_RELEASE:
            buka_baru()
        zf.write(k, os.path.basename(k))
        saiz += s
        os.remove(k)
    zf.close()
    os.rmdir(kerja)

    if len(besar) == 1:
        akhir = os.path.join(a.out, f"{asas}.zip")
        os.replace(besar[0], akhir)
        besar = [akhir]

    jumlah_mb = sum(os.path.getsize(x) for x in besar) / 1048576
    nota = (
        f"Sumber: {a.label}\n"
        f"Fail: {len(fail)} · ZIP kecil: {jum_bhg} ({per} fail setiap satu)"
        f" · Flatten: {'Ya' if flat else 'Tidak'}"
        f"{' · Tapisan: ' + a.filter if a.filter else ''}\n"
        f"Muat turun: {len(besar)} fail · {jumlah_mb:.1f}MB\n"
    )
    with open(os.path.join(a.out, "nota.txt"), "w", encoding="utf-8") as f:
        f.write(nota)
    print(nota)


if __name__ == "__main__":
    main()
