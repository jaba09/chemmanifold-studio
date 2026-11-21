import cantera as ct
g=ct.Solution('gri30.yaml')
drop={'AR','C3H7','C3H8','CH2CHO','CH3CHO','HCCOH','C2H','CH2CO','NH3','HCNN'}
sp=[s for s in g.species() if s.name not in drop]
names={s.name for s in sp}
rx=[]
for r in g.reactions():
    tb=getattr(r,"third_body",None)
    if tb is not None and tb.name not in ("M",) and tb.name not in names: continue
    if all(k in names for k in list(r.reactants)+list(r.products)):
        if hasattr(r,'third_body') and r.third_body is not None and r.third_body.efficiencies:
            r.third_body.efficiencies={k:v for k,v in r.third_body.efficiencies.items() if k in names}
        rx.append(r)
s=ct.Solution(thermo='ideal-gas',kinetics='gas',transport_model='mixture-averaged',species=sp,reactions=rx)
print(len(sp),len(rx))
s.write_yaml('gri30_skel43.yaml')
QSS="C CH CH2 CH2(S) HCO CH2OH CH3O C2H3 C2H5 HCCO N NH NH2 NNH HNO CN H2CN HCNO HOCN HNCO NCO".split()
n=0
for i,r in enumerate(rx):
    q=[k for k,v in r.reactants.items() for _ in range(int(v)) if k in QSS]
    qp=[k for k,v in r.products.items() for _ in range(int(v)) if k in QSS]
    if len(q)>=2 or len(qp)>=2: n+=1; print(i,r.equation)
print('QSS-QSS',n)
