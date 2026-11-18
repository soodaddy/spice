"""Lesson 12: N DRAM cells (access NMOS + storage node + Cs) sharing one bit line. Netlist builders and the hand formula.

ILLUSTRATIVE values (author's): Cs = 25 fF, wire capacitance of the bit line Cw = 145 fF, junction/contact capacitance per cell Cj = 5 fF
(so one cell gives Cbl = 150 fF, the value of lesson 11), Vdd = 1.2 V, Vpp = 2.0 V, access Vth = 0.7 V.
Level 1 has no sub-threshold current: an unselected cell (word line low) is perfectly isolated in these simulations.
"""

VDD, VPP, VTH, VBLP = 1.2, 2.0, 0.7, 0.6
CS, CW, CJ = 25e-15, 145e-15, 5e-15
VH = min(VDD, VPP - VTH)                                   # level written for a 1


def cbl_total(n, cw=CW, cj=CJ):
    return cw + n * cj


def hand_dv(levels, sel, n, cs=CS, cw=CW, cj=CJ):
    """Charge sharing of the selected cells with the precharged bit line: dV = sum(Cs (Vk - Vblp)) / (Cbl + m Cs)."""
    return sum(cs * (levels[k] - VBLP) for k in sel) / (cbl_total(n, cw, cj) + len(sel) * cs)


def models():
    return (f".model nacc nmos level=1 vto={VTH} kp=300u lambda=0.05\n.model nsw nmos level=1 vto=0.5 kp=300u lambda=0.05\n"
            ".model nsa nmos level=1 vto=0.4 kp=300u lambda=0.05\n.model psa pmos level=1 vto=-0.4 kp=100u lambda=0.05\n")


def share_net(bits, sel, cs=CS, cw=CW, cj=CJ, vpp=VPP):
    """Charge sharing only (no sense amplifier). bits: stored data of every cell; sel: cells whose word line is raised at 1 ns.
    The cells are set to their levels by switches that are open after 0.3 ns (minispice has no .ic)."""
    n = len(bits)
    s = f"{n} cells on one bit line, charge sharing\n" + models() + f"Vblp vblp 0 {VBLP}\nVeq eq 0 PULSE({vpp} 0 0.3n 0.1n 0.1n 100n 200n)\n"
    s += "Meq bl eq vblp 0 nsw W=1u L=0.1u\n"
    for k in range(n):
        lvl = VH if bits[k] else 0.0
        s += f"Vc{k} vc{k} 0 {lvl}\nMw{k} sn{k} eq vc{k} 0 nsw W=1u L=0.1u\nMa{k} bl wl{k} sn{k} 0 nacc W=0.1u L=0.1u\nCs{k} sn{k} 0 {cs}\n"
        s += (f"Vwl{k} wl{k} 0 PULSE(0 {vpp} 1n 0.2n 0.2n 20n 40n)\n" if k in sel else f"Vwl{k} wl{k} 0 0\n")
    s += f"Cbl bl 0 {cw + n * cj}\n.end\n"
    return s


def seq_net(bits, cs=CS, cw=CW, cj=CJ, vpp=VPP, slot=8e-9, rslot=16e-9):
    """Write the bits one cell after the other (a write driver switch per cell), then read every cell with the latch sense amplifier.
    Returns (netlist, info) with the times of every phase (seconds)."""
    n = len(bits)
    ns = lambda t: f"{t*1e9:.3f}n"
    r0 = n * slot + 2e-9
    s = f"{n} cells on one bit line: write {bits}, then read each\n" + models()
    s += f"Vblp vblp 0 {VBLP}\nVdd vdd 0 {VDD}\n"
    s += f"Veq eq 0 PULSE(0 {vpp} {ns(r0)} 0.1n 0.1n 2n {ns(rslot)})\n"
    s += f"Vsan san 0 PULSE({VBLP} 0 {ns(r0 + 6e-9)} 0.5n 0.5n 8n {ns(rslot)})\nVsap sap 0 PULSE({VBLP} {VDD} {ns(r0 + 6e-9)} 0.5n 0.5n 8n {ns(rslot)})\n"
    s += "Meq1 bl eq vblp 0 nsw W=1u L=0.1u\nMeq2 blb eq vblp 0 nsw W=1u L=0.1u\n"
    s += f"Cbl bl 0 {cw + n * cj - 2e-15}\nCblb blb 0 {cw + n * cj - 2e-15}\n"          # 2 fF of the total sits at the latch input (Cbs below)
    # The latch is connected to the bit lines through isolation switches that are open while the cells are written: with both latch supplies at Vdd/2 a latch
    # transistor conducts when a bit line is pulled to 0 V (Vgs = 0.6 V > Vth = 0.4 V) and would corrupt the written level.
    s += f"Viso iso 0 PULSE(0 {vpp} {ns(r0 - 0.3e-9)} 0.1n 0.1n 1u 2u)\nMi1 bl iso bls 0 nsw W=20u L=0.1u\nMi2 blb iso blbs 0 nsw W=20u L=0.1u\nCbs bls 0 2f\nCbbs blbs 0 2f\n"
    # floating nodes have no defined voltage (each simulator resolves them with its own gmin handling): hold BLB, BLS and BLBS at Vdd/2 until just before the first read
    s += f"Veq2 eq2 0 PULSE({vpp} 0 {ns(r0 - 0.5e-9)} 0.1n 0.1n 1u 1u)\nMe3 blb eq2 vblp 0 nsw W=1u L=0.1u\nMe4 bls eq2 vblp 0 nsw W=1u L=0.1u\nMe5 blbs eq2 vblp 0 nsw W=1u L=0.1u\n"
    s += "Mn1 bls blbs san 0 nsa W=2u L=0.1u\nMn2 blbs bls san 0 nsa W=2u L=0.1u\nMp1 bls blbs sap vdd psa W=4u L=0.1u\nMp2 blbs bls sap vdd psa W=4u L=0.1u\n"
    for k in range(n):
        tw = 1e-9 + k * slot
        s += f"Ma{k} bl wl{k} sn{k} 0 nacc W=0.1u L=0.1u\nCs{k} sn{k} 0 {cs}\n"
        s += f"Vwlw{k} wlw{k} 0 PULSE(0 {vpp} {ns(tw)} 0.2n 0.2n 5n 1u)\nVwlr{k} wl{k} wlw{k} PULSE(0 {vpp} {ns(r0 + k * rslot + 3e-9)} 0.2n 0.2n 9n 1u)\n"
        s += f"Vd{k} d{k} 0 {VDD if bits[k] else 0.0}\nVwe{k} we{k} 0 PULSE(0 {vpp} {ns(tw - 0.3e-9)} 0.2n 0.2n 5.6n 1u)\nMd{k} bl we{k} d{k} 0 nsw W=2u L=0.1u\n"
    s += ".end\n"
    return s, dict(r0=r0, slot=slot, rslot=rslot, tstop=r0 + n * rslot, t_sa=[r0 + k * rslot + 6e-9 for k in range(n)], t_wl_on=[r0 + k * rslot + 3e-9 for k in range(n)])
