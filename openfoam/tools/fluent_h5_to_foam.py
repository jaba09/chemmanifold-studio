#!/usr/bin/env python3
"""Convert a 2D axisymmetric Fluent mesh stored in a .cas.h5 file into an OpenFOAM wedge polyMesh.

fluentMeshToFoam only reads ASCII .msh/.cas files, so this reads the CFF/HDF5 mesh directly.
The 2D mesh is revolved about the x axis by +/- angle/2 into a one-cell-thick wedge; nodes on the
axis (y = 0) are not duplicated, so axis edges collapse and cells touching the axis become prisms.

Patch names are the Fluent zone names (':' replaced). Fluent "interior" zones become internal
faces and Fluent cell zones become cellZones. Axis zones produce no faces and are dropped.

Usage:
    python fluent_h5_to_foam.py case.cas.h5 <OpenFOAM case dir> [--angle 5] [--scale 1]
"""
import argparse
import os

import h5py
import numpy as np

# Fluent face-zone type codes -> OpenFOAM patch type
ZONE_TYPES = {2: "interior", 3: "wall", 4: "patch", 5: "patch", 7: "symmetryPlane",
              10: "patch", 20: "patch", 36: "patch", 37: "axis"}
FOAM_HEADER = """FoamFile
{{
    version     2.0;
    format      ascii;
    class       {cls};
    location    "constant/polyMesh";
    object      {obj};
}}
"""


def read_mesh(path):
    with h5py.File(path, "r") as f:
        m = f["meshes/1"]
        if int(m.attrs["dimension"][0]) != 2:
            raise SystemExit("only 2D meshes are supported")
        coords = np.concatenate([m["nodes/coords"][k][()] for k in m["nodes/coords"]])
        F = m["faces"]
        nface = int(m.attrs["faceCount"][0])
        nn = F["nodes/1/nnodes"][()]
        if not np.all(nn == 2):
            raise SystemExit("2D faces must have exactly two nodes")
        fnodes = F["nodes/1/nodes"][()].reshape(-1, 2).astype(np.int64) - 1
        c0 = np.zeros(nface, np.int64)
        c1 = np.zeros(nface, np.int64)
        for name, arr in (("c0", c0), ("c1", c1)):
            for k in F[name]:
                d = F[name][k]
                lo, hi = int(d.attrs["minId"][0]), int(d.attrs["maxId"][0])
                arr[lo - 1:hi] = d[()]
        fz = F["zoneTopology"]
        fzones = [dict(id=int(i), name=n, type=int(t), lo=int(a) - 1, hi=int(b))
                  for i, n, t, a, b in zip(fz["id"][()], fz["name"][0].decode().split(";"),
                                           fz["zoneType"][()], fz["minId"][()], fz["maxId"][()])]
        cz = m["cells/zoneTopology"]
        czones = [dict(id=int(i), name=n, lo=int(a) - 1, hi=int(b))
                  for i, n, a, b in zip(cz["id"][()], cz["name"][0].decode().split(";"),
                                        cz["minId"][()], cz["maxId"][()])]
        ncell = int(m.attrs["cellCount"][0])
    return coords, fnodes, c0 - 1, c1 - 1, fzones, czones, ncell


def cell_polygons(fnodes, c0, c1, ncell):
    """Ordered node loop of every 2D cell, chained from its edges."""
    edges = [[] for _ in range(ncell)]
    for e, (a, b) in enumerate(fnodes):
        edges[c0[e]].append((a, b))
        if c1[e] >= 0:
            edges[c1[e]].append((a, b))
    polys = []
    for c, el in enumerate(edges):
        nbr = {}
        for a, b in el:
            nbr.setdefault(a, []).append(b)
            nbr.setdefault(b, []).append(a)
        start = el[0][0]
        loop, prev, cur = [start], None, start
        while True:
            nxt = [n for n in nbr[cur] if n != prev]
            nxt = nxt[0] if prev is not None else nbr[cur][0]
            if nxt == start:
                break
            loop.append(nxt)
            prev, cur = cur, nxt
        if len(loop) != len(el):
            raise SystemExit(f"cell {c}: could not chain its {len(el)} edges")
        polys.append(loop)
    return polys


def newell(p):
    n = np.zeros(3)
    for i in range(len(p)):
        a, b = p[i], p[(i + 1) % len(p)]
        n += np.cross(a, b)
    return 0.5 * n


def write_list(path, cls, obj, items, fmt, note=""):
    with open(path, "w") as f:
        f.write(FOAM_HEADER.format(cls=cls, obj=obj) + (f"// {note}\n" if note else "") + "\n")
        f.write(f"{len(items)}\n(\n")
        for it in items:
            f.write(fmt(it) + "\n")
        f.write(")\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cas")
    ap.add_argument("case")
    ap.add_argument("--angle", type=float, default=5.0, help="total wedge angle in degrees")
    ap.add_argument("--scale", type=float, default=1.0, help="multiply coordinates (e.g. 0.001 for mm)")
    ap.add_argument("--axis-tol", type=float, default=1e-12, help="|y| below this is on the axis")
    args = ap.parse_args()

    xy, fnodes, c0, c1, fzones, czones, ncell = read_mesh(args.cas)
    xy = xy * args.scale
    if xy[:, 1].min() < -args.axis_tol:
        raise SystemExit("negative radial coordinates: the axis must be y = 0 with the mesh at y >= 0")
    nnode = len(xy)
    on_axis = np.abs(xy[:, 1]) <= args.axis_tol

    # wedge points: back (-theta) are 0..n-1, front (+theta) are appended for off-axis nodes only
    th = np.radians(args.angle / 2)
    back = np.column_stack([xy[:, 0], xy[:, 1] * np.cos(th), -xy[:, 1] * np.sin(th)])
    front_id = np.arange(nnode)
    off = np.where(~on_axis)[0]
    front_id[off] = nnode + np.arange(len(off))
    front = np.column_stack([xy[off, 0], xy[off, 1] * np.cos(th), xy[off, 1] * np.sin(th)])
    pts = np.vstack([back, front])

    polys = cell_polygons(fnodes, c0, c1, ncell)
    cc = np.array([pts[np.r_[p, front_id[p]]].mean(axis=0) for p in polys])

    zone_of_face = np.empty(len(fnodes), np.int64)
    for zi, z in enumerate(fzones):
        zone_of_face[z["lo"]:z["hi"]] = zi

    def oriented(face, owner, outward_ref):
        n = newell(pts[face])
        ctr = pts[face].mean(axis=0)
        return face if np.dot(n, ctr - outward_ref) > 0 else face[::-1]

    internal, bfaces = [], {}
    for e, (a, b) in enumerate(fnodes):
        z = fzones[zone_of_face[e]]
        ztype = ZONE_TYPES.get(z["type"], "patch")
        if on_axis[a] and on_axis[b]:
            if ztype != "axis":
                print(f"warning: face {e} of zone {z['name']} lies on the axis and is dropped")
            continue
        quad = [a, b, front_id[b], front_id[a]]
        face = list(dict.fromkeys(quad))  # collapse the duplicated axis node
        if c1[e] >= 0:
            o, nb = sorted((c0[e], c1[e]))
            internal.append((o, nb, oriented(face, o, cc[o])))
        else:
            o = c0[e]
            bfaces.setdefault(z["name"], []).append((o, oriented(face, o, cc[o])))

    wedge = {"back": [], "front": []}
    for c, p in enumerate(polys):
        wedge["back"].append((c, oriented(list(p), c, cc[c])))
        wedge["front"].append((c, oriented([front_id[i] for i in p], c, cc[c])))

    internal.sort(key=lambda t: (t[0], t[1]))
    faces = [t[2] for t in internal]
    owner = [t[0] for t in internal]
    neigh = [t[1] for t in internal]
    patches = []
    for z in fzones:
        if z["name"] not in bfaces:
            continue
        ft = ZONE_TYPES.get(z["type"], "patch")
        lst = sorted(bfaces[z["name"]], key=lambda t: t[0])
        patches.append((z["name"].replace(":", "-"), ft, z, len(faces), len(lst)))
        faces += [t[1] for t in lst]
        owner += [t[0] for t in lst]
    for name in ("back", "front"):
        patches.append((name, "wedge", None, len(faces), len(wedge[name])))
        faces += [t[1] for t in wedge[name]]
        owner += [t[0] for t in wedge[name]]

    # Fluent two-sided walls (wall + wall-shadow) become a mappedWall pair for a coupled baffle
    names = {p[0] for p in patches}

    mesh = os.path.join(args.case, "constant", "polyMesh")
    os.makedirs(mesh, exist_ok=True)
    note = f"converted from {os.path.basename(args.cas)}: {args.angle} deg wedge about the x axis"
    write_list(os.path.join(mesh, "points"), "vectorField", "points", pts,
               lambda p: f"({p[0]:.12g} {p[1]:.12g} {p[2]:.12g})", note)
    write_list(os.path.join(mesh, "faces"), "faceList", "faces", faces,
               lambda f: f"{len(f)}(" + " ".join(map(str, f)) + ")", note)
    write_list(os.path.join(mesh, "owner"), "labelList", "owner", owner, str,
               f"nPoints:{len(pts)} nCells:{ncell} nFaces:{len(faces)} nInternalFaces:{len(internal)}")
    write_list(os.path.join(mesh, "neighbour"), "labelList", "neighbour", neigh, str,
               f"nPoints:{len(pts)} nCells:{ncell} nFaces:{len(faces)} nInternalFaces:{len(internal)}")

    with open(os.path.join(mesh, "boundary"), "w") as f:
        f.write(FOAM_HEADER.format(cls="polyBoundaryMesh", obj="boundary") + "\n")
        f.write(f"{len(patches)}\n(\n")
        for name, ft, z, start, n in patches:
            f.write(f"    {name}\n    {{\n")
            shadow = name[:-len("-shadow")] if name.endswith("-shadow") else name + "-shadow"
            if ft == "wall" and shadow in names:
                f.write("        type            mappedWall;\n        inGroups        List<word> 1(wall);\n"
                        "        sampleMode      nearestPatchFace;\n        sampleRegion    region0;\n"
                        f"        samplePatch     {shadow};\n        offsetMode      uniform;\n"
                        "        offset          (0 0 0);\n")
            elif ft == "wall":
                f.write("        type            wall;\n        inGroups        List<word> 1(wall);\n")
            else:
                f.write(f"        type            {ft};\n")
            if z is not None:
                f.write(f"        // Fluent zone {z['id']}, type code {z['type']}\n")
            f.write(f"        nFaces          {n};\n        startFace       {start};\n    }}\n")
        f.write(")\n")

    with open(os.path.join(mesh, "cellZones"), "w") as f:
        f.write(FOAM_HEADER.format(cls="regIOobject", obj="cellZones") + "\n")
        f.write(f"{len(czones)}\n(\n")
        for z in czones:
            ids = range(z["lo"], z["hi"])
            f.write(f"{z['name']}\n{{\n    type cellZone;\ncellLabels List<label> {len(ids)}\n(\n")
            f.write("\n".join(map(str, ids)) + "\n)\n;\n}\n")
        f.write(")\n")

    print(f"{len(pts)} points, {ncell} cells, {len(faces)} faces ({len(internal)} internal)")
    for name, ft, z, start, n in patches:
        print(f"  {name:40s} {ft:14s} {n}")


if __name__ == "__main__":
    main()
