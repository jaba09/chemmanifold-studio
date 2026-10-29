import numpy as np, re, os
def read_field(path, n=None):
    s = open(path).read()
    m = re.search(r"internalField\s+(uniform|nonuniform)\s+", s)
    if m.group(1) == "uniform":
        v = s[m.end():].split(";")[0].strip()
        return float(v) if not v.startswith("(") else np.array(v.strip("()").split(), float)
    rest = s[m.end():]
    m2 = re.search(r"List<(\w+)>\s*(\d+)\s*\(", rest)
    typ, cnt = m2.group(1), int(m2.group(2))
    body = rest[m2.end():]
    if typ == "scalar":
        return np.array(body[:body.index(")")].split(), float)[:cnt]
    end = body.index("\n)")
    return np.array(body[:end].replace("(", " ").replace(")", " ").split(), float).reshape(cnt, 3)
