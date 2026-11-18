"""HTML for each lesson. Every number comes from data.py or from examples/out/lessonN.json."""

import base64
import html
import json
import pathlib

import data

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "examples" / "out"


# ---------------------------------------------------------------- helpers
def si(x, unit="", digits=3):
    """Engineering-prefix formatting: 2.27e-4 -> '227 µ' + unit."""
    if x == 0:
        return f"0 {unit}".strip()
    pre = [(1e-15, "f"), (1e-12, "p"), (1e-9, "n"), (1e-6, "µ"), (1e-3, "m"), (1, ""), (1e3, "k")]
    a = abs(x)
    for scale, p in reversed(pre):
        if a >= scale * 0.9995:
            return f"{x / scale:.{digits}g} {p}{unit}".strip()
    return f"{x:.3g} {unit}".strip()


def fx(x, n=3):
    return f"{x:.{n}f}"


def tbl(head, rows, cls=""):
    th = "".join(f"<th>{h}</th>" for h in head)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<div class="tw"><table class="{cls}"><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>'


def box(kind, title, body):
    return f'<aside class="box {kind}"><strong>{title}</strong>{body}</aside>'


def code(text):
    return f"<pre><code>{html.escape(text.strip(chr(10)))}</code></pre>"


def eq(text):
    return f'<pre class="eq">{html.escape(text.strip(chr(10)))}</pre>'


def details(summary, body):
    return f"<details><summary>{summary}</summary>{body}</details>"


def fig(name, caption):
    b = base64.b64encode((OUT / f"{name}.png").read_bytes()).decode()
    return (f'<figure><img alt="{html.escape(caption)}" src="data:image/png;base64,{b}"><figcaption>{caption}</figcaption></figure>')


def J(n):
    return json.loads((OUT / f"lesson{n}.json").read_text())


def head(n, title, goal):
    return f'<section id="l{n}" class="lesson"><h2><span class="num">{n}</span>{title}</h2><p class="goal"><b>학습 목표</b> {goal}</p>'


STATUS = {
    "ok": '<span class="st ok">실행·검증됨</span>',
    "part": '<span class="st part">부분 검증</span>',
    "no": '<span class="st no">미실행</span>',
}


# ---------------------------------------------------------------- lesson 1
def lesson1():
    d = data.lesson1()
    r0 = d["rows"][0]
    rows = [(f"Vgs = {a:.1f}, Vds = {b:.1f}", c, f"{e*1e6:.3f} µA", f"{f*1e6:.3f} µA") for a, b, c, e, f in d["rows"]]
    g0, g1 = d["gds_examples"]
    s = head(1, "평면형 NMOS 하나의 I-V", "트랜지스터를 “전압 4개를 받아 전류 하나를 내놓는 함수”로 이해하고, 영역별 식을 손으로 계산해서 코드와 맞춰 본다.")
    s += f"""
<h3>1.1 소자를 함수로 본다</h3>
<p>SPICE에서 MOSFET은 단자 전압 4개(드레인 d, 게이트 g, 소스 s, 벌크 b)를 받아 드레인 전류 <code>Id</code>를 내놓는 함수입니다. 이 함수를 정하는 것이 <b>compact model</b>이고, 이 레슨에서는 가장 단순한 Level 1(Shichman–Hodges)을 씁니다.</p>
{eq("(Vd, Vg, Vs, Vb)  →  Id      (Id: 드레인 단자로 들어가는 전류)")}
{box("info", "Vgs, Vds의 아래 첨자", "<p>아래 첨자 <code>s</code>는 static이 아니라 <b>source(소스)</b>입니다. <code>Vxy</code>는 <b>x 단자 전압에서 y 단자 전압을 뺀 값</b>입니다: <code>Vgs = Vg − Vs</code>, <code>Vds = Vd − Vs</code>. NMOS는 게이트와 <i>소스</i> 사이 전압 차이가 채널을 만들기 때문에 모델 식이 모두 Vgs, Vds로 쓰입니다. netlist의 <code>Vds d 0 1.8</code>에서 맨 앞 <code>V</code>는 “전압원”이라는 SPICE 문법이고 <code>ds</code>는 그냥 붙인 이름입니다.</p>")}
{fig("lesson1", "그림 1-1. (a) 회로 기호와 시험 회로, (b) 같은 소자의 단면(평면형 NMOS), (c) 출력 특성, (d) √Id–Vgs")}

<h3>1.2 파라미터: β, Vth, λ</h3>
{tbl(["기호", "값", "의미"], [
    ["VTO (Vth)", "0.5 V", "문턱전압. 이 이상 게이트를 올려야 채널(반전층)이 생김"],
    ["KP", "300 µA/V²", "µn·Cox. 공정이 정하는 값"],
    ["W / L", "1 µm / 0.18 µm", "설계자가 정하는 모양 (단면도의 L, 종이에 수직인 W)"],
    ["β = KP·W/L", f"<b>{d['beta']*1e3:.4f} mA/V²</b>", "소자의 전류 구동 능력"],
    ["λ (LAMBDA)", "0.05 /V", "채널 길이 변조: 포화에서 Vds가 커지면 Id가 조금 늘어나는 정도"]])}
{details("β와 λ는 어떻게 구하나? (심화)", f'''
<p><b>β는 계산</b>합니다. <code>KP = µn·Cox</code>, <code>Cox = εox/tox</code>. 예: tox = 4 nm → Cox = 8.63 fF/µm², µn = 350 cm²/V·s이면 KP ≈ {d["kp_phys"]*1e6:.0f} µA/V². 측정에서 거꾸로 구할 때는 포화 영역의 √Id가 Vgs에 대해 직선이라는 점을 씁니다: 기울기 m = √(β(1+λVds)/2) → β = 2m²/(1+λVds). 이 모델에서 기울기는 {d["slope"]*1e3**0.5:.4f} √mA/V이고 β = {d["beta_from_slope"]*1e3:.4f} mA/V²로 원래 값이 복원됩니다.</p>
<p><b>λ는 측정</b>해서 구합니다. 같은 Vgs에서 포화 영역의 두 점 (Vds₁, I₁), (Vds₂, I₂)로 <code>λ = (I₂−I₁)/(I₁Vds₂ − I₂Vds₁)</code>. Vgs = 1.0 V에서 I₁ = {d["lam_i1"]*1e6:.3f} µA (Vds = 1.0), I₂ = {d["lam_i2"]*1e6:.3f} µA (Vds = 1.8)이면 λ = {d["lam"]:.4f} /V. 채널이 짧을수록 λ가 커지지만(λ ∝ 1/L), Level 1에서는 입력하는 고정값이라 L을 바꿔도 자동으로 변하지 않습니다.</p>''')}

<h3>1.3 세 가지 동작 영역</h3>
<p><code>Vov = Vgs − Vth</code>를 <b>과구동 전압</b>이라고 부릅니다. 게이트를 문턱보다 얼마나 더 올렸는지를 나타내고, 전류의 크기와 영역 경계를 정합니다.</p>
{tbl(["영역", "조건", "식"], [
    ["차단 (cutoff)", "Vov ≤ 0", "Id = 0"],
    ["선형 (triode)", "Vds &lt; Vov", "Id = β·(Vov − Vds/2)·Vds·(1 + λVds)"],
    ["포화 (saturation)", "Vds ≥ Vov", "Id = ½β·Vov²·(1 + λVds)"]])}
<p>경계가 <code>Vds = Vov</code>인 이유: 채널이 드레인 쪽 끝까지 이어져 있으려면 <b>게이트–드레인 전압</b>도 문턱을 넘어야 합니다. <code>Vgd = Vgs − Vds &gt; Vth ⟺ Vds &lt; Vov</code>. 이 조건이 깨지면 드레인 쪽 채널이 끊깁니다(pinch-off).</p>

<h3>1.4 손 계산과 코드의 비교</h3>
{tbl(["바이어스", "영역", "손 계산", "코드"], [list(r) for r in rows])}
<p>첫 행을 직접 따라 해 봅니다. Vov = 1.0 − 0.5 = 0.5 V → ½ · {d["beta"]*1e3:.4f}m · 0.25 = {0.5*d["beta"]*0.25*1e6:.2f} µA, 여기에 (1 + 0.05·1.8) = 1.09를 곱하면 <b>{r0[3]*1e6:.3f} µA</b>입니다.</p>

<h3>1.5 같은 점을 SPICE <code>.op</code>로 풀면</h3>
{code("""Lesson 1: single NMOS
.model nch nmos level=1 vto=0.5 kp=300u lambda=0.05
Vgs g 0 1.0
Vds d 0 1.8
M1 d g 0 0 nch W=1u L=0.18u
.op
.end""")}
<p>결과는 <code>i(vds) = {d["op_i"]*1e6:.3f} µA</code>입니다. 음수인 것은 <b>SPICE 부호 규칙</b> 때문입니다. 전압원의 전류는 + 단자로 들어가는 방향이 양수인데, 이 소스는 전류를 내보내고 있기 때문입니다. 그래서 <code>Id = −i(vds)</code>로 읽고 값은 손 계산과 같습니다.</p>

<h3>1.6 기울기 gm, gds</h3>
<p>모델은 전류뿐 아니라 기울기도 함께 돌려줍니다. Vgs = 1.0, Vds = 1.8 V에서 <code>gm = ∂Id/∂Vg = {d["gm"]*1e6:.1f} µS</code>, <code>gds = ∂Id/∂Vd = {d["gds"]*1e6:.2f} µS</code>입니다. 이 기울기를 어디에 쓰는지가 레슨 2의 주제입니다.</p>
{details("gds는 어떻게 계산하나? (심화)", f'''
<p>선형 영역의 식 <code>Id = β(Vov·Vds − Vds²/2)·(1 + λVds)</code>를 Vds로 미분합니다(곱의 미분).</p>
{eq("gds = β(Vov − Vds)(1 + λVds)  +  λ·β(Vov − Vds/2)·Vds")}
<p>포화 영역은 Vds가 (1+λVds)에만 들어 있으므로 <code>gds = λ·½β·Vov²</code>입니다. 레슨 2의 숫자(Vg = 1.4 V, Vov = 0.9 V)로 계산하면: Vds = 0일 때 {g0[3]*1e6:.0f} µS, Vds = 0.21176 V일 때 첫째 항 {g1[1]*1e6:.1f} µS + 둘째 항 {g1[2]*1e6:.1f} µS = <b>{g1[3]*1e6:.1f} µS</b>입니다. Vds가 아주 작으면 Id ≈ β·Vov·Vds이므로 트랜지스터는 Ron = 1/(β·Vov) ≈ {1/(d["beta"]*0.9):.0f} Ω의 저항처럼 동작하고, 포화에서는 gds가 작아서 전류원처럼 동작합니다.</p>''')}

<h3>1.7 이 모델의 한계</h3>
<p>차단 영역에서 Id가 정확히 0입니다(그림 1-1 (d)의 Vgs &lt; 0.5 V). 실제 소자는 문턱 아래에서도 전류가 지수적으로 흐르는데, 그 부분이 레슨 5의 EKV 모델입니다.</p>
{box("ok", "요약", "<ul><li>MOSFET = (Vd, Vg, Vs, Vb) → Id 함수 + 그 기울기</li><li>Vov = Vgs − Vth, 영역 경계는 Vds = Vov</li><li>β = KP·W/L은 계산, λ는 측정으로 구한다</li></ul>")}
<p class="run">직접 해 보기: <code>python examples/lesson1_single_mosfet.py</code></p></section>"""
    return s


# ---------------------------------------------------------------- lesson 2
def lesson2():
    d = data.lesson2()
    rows = [[r["k"], f"{r['vd0']:.5f}", f"{r['id0']*1e6:.2f}", f"{r['gds']*1e6:.1f}", f"{r['ieq']*1e6:.2f}", f"<b>{r['vd1']:.6f}</b>"] for r in d["rows"][:4]]
    r1, r2 = d["rows"][0], d["rows"][1]
    errs = d["errs"]
    err_chain = " → ".join(f"{e:.0e}" for e in errs[:4]) + " → ~1e-15"
    log = [[it, f"{xb:.4f} → {xa:.4f}", f"{gb:.4f} → {ga:.4f}", "예" if dmp else "아니오"] for it, xb, xa, gb, ga, dmp in d["log"]]
    s = head(2, "저항을 달면: Newton 반복으로 동작점 구하기", "비선형 방정식을 SPICE가 어떻게 푸는지, “접선으로 바꿔서 푼다”는 아이디어를 손 계산으로 따라간다.")
    s += f"""
<h3>2.1 문제</h3>
<p>레슨 1에서는 Vds를 우리가 정했습니다. 이번에는 드레인에 <b>저항 5 kΩ</b>을 달아서 <b>Vd를 회로가 정하게</b> 합니다. 키르히호프 전류 법칙(KCL)에 따라 저항이 공급하는 전류와 트랜지스터가 흘려보내는 전류는 같아야 합니다.</p>
{eq("(Vdd − Vd) / Rd  =  Id(Vd)\n  └ 직선(부하선)        └ 곡선(레슨 1의 식)")}
{fig("lesson2", "그림 2-1. (a) 회로, (b) 한 Newton 스텝: 트랜지스터를 gds ∥ Ieq로 바꾼다, (c) 접선과 부하선의 교점이 다음 추측값, (d) 오차 감소")}
<p>오른쪽이 Vd의 비선형 식이고 영역에 따라 식이 바뀌므로 공식 하나로 바로 풀 수 없습니다. 그래서 <b>추측 → 개선</b>을 반복합니다.</p>

<h3>2.2 Newton의 아이디어: 곡선을 접선으로 바꾼다</h3>
<p>현재 추측값 Vd0에서 곡선에 <b>접선</b>을 긋습니다. 직선과 직선의 교점은 쉽게 구할 수 있고, 그 점이 다음 추측값입니다. 그림 2-1 (b)는 이 접선을 회로로 그린 것입니다. 트랜지스터가 <b>저항 gds와 전류원 Ieq의 병렬</b>로 바뀝니다(companion model).</p>
{eq("Id ≈ gds·Vd + Ieq,     Ieq = Id0 − gds·Vd0\nVd = (Vdd/Rd − Ieq) / (1/Rd + gds)")}
<ol><li>현재 Vd0에서 모델로 Id0와 gds를 구한다.</li><li>트랜지스터를 gds ∥ Ieq로 바꾼다.</li><li>선형 회로를 풀어서 새 Vd를 얻는다. 값이 안 변할 때까지 반복.</li></ol>

<h3>2.3 손으로 따라 하기 (Vg = 1.4 V, 시작 Vd = 0)</h3>
{tbl(["스텝", "Vd0 [V]", "Id0 [µA]", "gds [µS]", "Ieq [µA]", "새 Vd [V]"], rows)}
<p>스텝 1: Vd0 = 0이면 Id0 = 0, gds = β·Vov = {data.BETA*1e3:.4f}m × 0.9 = <b>{r1["gds"]*1e3:.1f} mS</b>, Ieq = 0 → Vd = (1.8/5k − 0)/(1/5k + 1.5m) = <b>{r1["vd1"]:.4f} V</b>. 스텝 2는 Vd0 = {r2["vd0"]:.4f}에서 Ieq = {r2["id0"]*1e6:.2f} − {r2["gds"]*1e6:.1f}×{r2["vd0"]:.4f} = {r2["ieq"]*1e6:.2f} µA이고 Vd = {r2["vd1"]:.4f} V가 됩니다.</p>

<h3>2.4 결과와 확인</h3>
<ul>
<li><b>Vd* = {d["star"]:.6f} V</b>, Id = {d["id_star"]*1e6:.2f} µA. 저항 쪽 전류 (Vdd−Vd)/Rd = {(data.VDD-d["star"])/data.RD*1e6:.4f} µA와 트랜지스터 Id가 같습니다(KCL 만족).</li>
<li>Vds = {d["star"]:.3f} V &lt; Vov = 0.9 V이므로 <b>선형(triode) 영역</b>에서 동작합니다.</li>
<li>minispice 솔버의 결과 {d["solver"]:.6f} V와 차이 {abs(d["solver"]-d["star"]):.1e} V.</li>
<li>오차가 매 스텝 대략 <b>제곱</b>으로 줄어듭니다(quadratic convergence): {err_chain} V.</li></ul>

<h3>2.4b 참고: 실제 솔버의 반복 로그</h3>
<p>위 계산은 변수를 Vd 하나로 줄인 것이고, 실제 솔버는 <b>모든 미지수(Vdd, Vg, Vd, 소스 전류)를 한꺼번에</b> 풉니다. 그래서 처음 반복들은 전압원을 0 V에서 올리는 데 쓰입니다. 한 번에 너무 크게 움직이면 접선 근사가 틀려 발산하므로, 한 반복에서 노드 전압이 1 V를 넘게 변하지 못하게 제한합니다.</p>
{tbl(["반복", "Vd (전 → 후)", "Vg (전 → 후)", "스텝 제한"], log)}
<p>반복 3부터가 위의 손 계산과 비슷한 과정입니다(이때 Vg가 1.38 → 1.40 V로 마무리되는 중이라 값이 조금 다릅니다).</p>
{box("ok", "요약", "<ul><li>비선형 소자는 현재 추측점에서의 접선(gds 저항 + Ieq 전류원)으로 바꿔서 푼다.</li><li>그 선형 회로의 해가 다음 추측값이고, 안 변할 때까지 반복한다.</li><li>레슨 1에서 모델이 전류와 기울기를 같이 돌려주는 이유가 이것이다.</li></ul>")}
<p class="run">직접 해 보기: <code>python examples/lesson2_newton.py</code></p></section>"""
    return s


# ---------------------------------------------------------------- lesson 3
def lesson3():
    d = data.lesson3()
    rows = [[r["it"], f"{r['v0']:.5f}", f"{r['i0']*1e6:.2f}", f"{r['gds']*1e6:.1f}", f"{r['ieq']*1e6:.2f}", f"<b>{r['v1']:.6f}</b>"] for r in d["rows"]]
    s = head(3, "커패시터를 달면: 시간 스텝으로 풀기 (transient)", "커패시터가 “매 스텝마다 저항과 전류원으로 바뀐다”는 것을 이해하고, 한 시간 스텝을 손으로 풀어 본다.")
    s += f"""
<h3>3.1 달라지는 점</h3>
<p>레슨 2의 회로에서 드레인에 <b>커패시터 CL = 100 fF</b>를 달고 게이트에 0 → 1.4 V 펄스를 넣습니다. 커패시터 전류 <code>i = C·dV/dt</code>가 KCL에 들어오므로 식이 <b>미분방정식</b>이 됩니다.</p>
{eq("(Vd − Vdd)/Rd  +  Id(Vd, Vg)  +  C·dVd/dt  =  0")}
{fig("lesson3", "그림 3-1. (a) 회로, (b) 한 시간 스텝에서 커패시터가 Geq ∥ Ieq로 바뀜(Backward Euler), (c) 전압 파형, (d) 전류 파형: iR = iD + iC")}

<h3>3.2 SPICE의 해법: 시간을 조각내서 미분을 차분으로 바꾼다</h3>
<p>시간을 간격 h(여기서는 20 ps)로 자르고 <code>dVd/dt ≈ (Vd_new − Vd_old)/h</code>로 바꿉니다(<b>Backward Euler</b>). 그러면 커패시터 전류가 이렇게 됩니다.</p>
{eq("i = (C/h)·Vd_new − (C/h)·Vd_old = Geq·Vd_new + Ieq\n    Geq = C/h,   Ieq = −Geq·Vd_old")}
<p>그림 3-1 (b)가 이 변환입니다. <b>커패시터가 매 스텝마다 저항 Geq와 전류원 Ieq의 병렬로 바뀝니다.</b> Geq = 100f/20p = <b>{d["geq"]*1e3:.0f} mS</b>로 Rd의 1/Rd = 0.2 mS보다 훨씬 커서, 한 스텝 동안 노드 전압은 이전 값을 강하게 붙잡고 조금씩만 변합니다. 결국 transient는 <b>“스텝마다 레슨 2의 Newton 문제를 한 번씩 푸는 것”</b>이고, 커패시터가 Geq와 Ieq로 추가될 뿐입니다.</p>

<h3>3.3 한 스텝을 손으로 풀기 ({d["t_a"]*1e9:.2f} ns → {d["t_b"]*1e9:.2f} ns)</h3>
<p>이전 스텝 결과 Vd_old = {d["vd_old"]:.6f} V, 게이트는 Vg = {d["vg_new"]:.1f} V입니다. 레슨 2의 식에 커패시터 항만 더합니다.</p>
{eq("Vd = ( Vdd/Rd − Ieq_fet + Geq·Vd_old ) / ( 1/Rd + gds + Geq )")}
{tbl(["반복", "Vd0 [V]", "Id0 [µA]", "gds [µS]", "Ieq_fet [µA]", "새 Vd [V]"], rows)}
<ul><li>손 계산 {d["vd_new_hand"]:.6f} V, 솔버 {d["vd_new_solver"]:.6f} V (차이 {abs(d["vd_new_hand"]-d["vd_new_solver"]):.1e} V).</li>
<li>전류 확인: 저항 {d["i_r"]*1e6:.1f} µA = 트랜지스터 {d["i_d"]*1e6:.1f} µA + 커패시터 <b>{d["i_c"]*1e6:.1f} µA</b>. 음수는 CL이 방전 중이라는 뜻입니다.</li></ul>

<h3>3.4 결과 읽는 법</h3>
{tbl(["항목", "값", "해석"], [
    ["낮은 쪽 전압", f"{d['vlow']:.4f} V", "레슨 2의 DC 답(0.2372 V)과 일치: 시간이 지나면 transient가 DC 해로 수렴"],
    ["내려갈 때 (90→10 %)", f"{d['fall']*1e12:.0f} ps", "트랜지스터가 최대 약 0.73 mA를 끌어당김"],
    ["올라갈 때 (10→90 %)", f"{d['rise']*1e12:.0f} ps", f"Rd만 CL을 충전. RC 이론값 2.2·Rd·CL = {d['rc22']*1e12:.0f} ps와 거의 같음"],
    ["지연 (Vg 50 % → Vd 50 %)", f"내림 {d['tp_fall']*1e12:.0f} ps / 올림 {d['tp_rise']*1e12:.0f} ps", "비대칭: 구동력이 다르다"]])}
<h3>3.5 시간 스텝과 방법에 따른 정확도</h3>
<p>1 ps 간격 trapezoidal 결과를 기준으로 비교하면 h = 20 ps에서 최대 오차가 Backward Euler <b>{d["err_be"]*1e3:.1f} mV</b>, trapezoidal <b>{d["err_trap"]*1e3:.1f} mV</b>입니다. 이 레슨은 설명이 쉬운 Backward Euler로 풀었습니다. 또한 펄스 에지가 시간 스텝 한가운데 있으면 trapezoidal이 크게 틀리므로(첫 스텝 결과가 절반이 됨), 솔버는 소스의 꺾이는 점에 시간 점을 강제로 맞춥니다(breakpoint).</p>
{box("warn", "이 예제의 한계", "<p>트랜지스터 자체의 내부 용량(게이트 용량 등)이 없고 커패시터는 외부 CL뿐입니다. 실제 소자는 내부 용량 때문에 지연이 더 커집니다. 이 부분은 레슨 6에서 다룹니다.</p>")}
{box("ok", "요약", "<ul><li>커패시터는 매 스텝 Geq(=C/h) ∥ Ieq(=−Geq·v_old)로 바뀐다.</li><li>스텝마다 레슨 2의 Newton을 푼다.</li><li>방법(BE/trap)과 h가 정확도를 정한다.</li></ul>")}
<p class="run">직접 해 보기: <code>python examples/lesson3_transient.py</code></p></section>"""
    return s


# ---------------------------------------------------------------- lesson 4
def _overshoot():
    """Newton step of the inverter at Vin = 0.6 V when started at Vout = 0.9 V (PMOS saturated)."""
    from minispice import Level1
    nm = Level1(1, dict(vto=0.5, kp=300e-6, lambda_=0.05))
    pm = Level1(-1, dict(vto=-0.5, kp=100e-6, lambda_=0.05))
    vo = 0.9
    idn, gn = nm.evaluate(vo, 0.6, 0, 0, 1e-6, 0.18e-6)[:2]
    idp, gp = pm.evaluate(vo, 0.6, 1.8, 1.8, 3e-6, 0.18e-6)[:2]
    return vo - (idn + idp) / (gn + gp)


def lesson4():
    k = J(4)
    d3 = data.lesson3()
    over = _overshoot()
    nw = k["newton"]
    nrows = [[r["it"], f"{r['vo']:.6f}", f"{r['idn']*1e6:.3f}", f"{r['isd']*1e6:.3f}", f"{r['gdsn']*1e6:.2f}", f"{r['gdsp']*1e6:.1f}", f"<b>{r['vnew']:.6f}</b>"] for r in nw[:3]]
    s = head(4, "CMOS 인버터: NMOS와 PMOS를 함께", "PMOS를 NMOS의 거울상으로 읽고, 인버터의 스위칭 문턱·이득·정적 전류·지연을 손으로 구해 솔버와 맞춰 본다.")
    s += f"""
<h3>4.1 PMOS 읽는 법</h3>
<p>레슨 2의 저항 Rd를 <b>PMOS</b>로 바꾼 것이 CMOS 인버터입니다. PMOS는 NMOS의 부호만 뒤집은 거울상입니다.</p>
{tbl(["", "NMOS", "PMOS"], [
    ["기준 단자", "소스(접지 쪽)", "소스(Vdd 쪽)"],
    ["제어 전압", "Vgs = Vg − Vs", "<b>Vsg</b> = Vs − Vg"],
    ["양단 전압", "Vds", "<b>Vsd</b> = Vs − Vd"],
    ["문턱전압 (SPICE 입력)", "VTO = +0.5 V", "VTO = <b>−0.5 V</b> (내부에서는 |Vtp| = 0.5 V)"],
    ["켜지는 조건", "Vin &gt; 0.5 V", "Vin &lt; Vdd − |Vtp| = 1.3 V"],
    ["전류 방향", "드레인 → 소스", "소스 → 드레인"]])}
<p>정공의 이동도가 전자의 약 1/3이므로 PMOS의 폭을 3배(3 µm)로 해서 두 트랜지스터의 β를 맞춥니다: βn = 300µ·1/0.18 = <b>{k["beta_n"]*1e3:.4f} mA/V²</b>, βp = 100µ·3/0.18 = <b>{k["beta_p"]*1e3:.4f} mA/V²</b>. 그래서 회로가 위아래 대칭입니다.</p>
{fig("lesson4", "그림 4-1. (a) CMOS 인버터, (b) CMOS 단면(NMOS는 p 기판, PMOS는 n-well 안), (c) VTC와 두 트랜지스터의 동작 영역, (d) 전원 전류, (e) 과도 응답, (f) 스위칭 중 전원 전류")}

<h3>4.2 손 계산 ① 스위칭 문턱 Vm</h3>
<p>Vout = Vin이 되는 점 Vm에서는 두 트랜지스터가 모두 포화이고 전류가 같습니다. λ를 무시하면</p>
{eq("βn (Vm − Vtn)²  =  βp (Vdd − Vm − |Vtp|)²\nVm = ( Vdd − |Vtp| + √(βn/βp)·Vtn ) / ( 1 + √(βn/βp) )")}
<p>βn = βp이므로 Vm = (1.8 − 0.5 + 0.5)/2 = <b>{k["vm_ideal"]:.4f} V</b>입니다. 솔버(VTC 교점)는 <b>{k["vm"]:.4f} V</b>로 같습니다.</p>

<h3>4.3 손 계산 ② 이득과 단락 전류</h3>
<p>Vm에서 gm과 gds는 레슨 1의 식으로 구합니다: gmn = gmp = {k["gmn"]*1e3:.4f} mS, gdsn = gdsp = {k["gdsn"]*1e6:.2f} µS. 소신호 이득은 gm의 합을 gds의 합으로 나눈 값입니다.</p>
{eq(f"|이득| = (gmn + gmp) / (gdsn + gdsp) = {k['gain_hand']:.1f}")}
<p>VTC를 수치로 미분한 최대 기울기는 <b>{k["gain_num"]:.1f}</b>로 같습니다. 이 때문에 VTC가 Vm 근처에서 거의 수직으로 떨어집니다. 이때 두 트랜지스터를 동시에 흐르는 전류는 ½βn·Vov²(1+λVm) = <b>{k["i_sc_hand"]*1e6:.1f} µA</b>이고, 솔버가 낸 전원 전류의 최대값은 {k["i_sc_peak"]*1e6:.1f} µA입니다.</p>

<h3>4.4 VTC와 동작 영역 (그림 4-1 (c))</h3>
{tbl(["Vin 구간", "NMOS", "PMOS", "Vout"], [
    ["0 ~ 0.5 V", "차단", "선형", "≈ Vdd (1.8 V)"],
    ["0.5 ~ 0.9 V", "포화", "선형", "Vdd 근처에서 서서히 하락"],
    ["≈ 0.9 V (Vm)", "포화", "포화", "급격히 하락 (이득 ≈ 100)"],
    ["0.9 ~ 1.3 V", "선형", "포화", "0 V 근처로 수렴"],
    ["1.3 ~ 1.8 V", "선형", "차단", "≈ 0 V"]])}
<p>(구간은 시뮬레이션에서 읽은 값입니다.) <b>Vin이 0 또는 Vdd일 때는 한쪽이 꺼져 있어서 전원에서 접지로 가는 길이 막힙니다.</b> 그림 4-1 (d)의 정적 전류 {k["i_static_0"]:.1e} A는 소자 누설이 아니라 솔버가 모든 노드에 넣는 <code>gmin = 10⁻¹² S</code> 때문입니다(레슨 5 참고). 레슨 2의 저항 부하는 켜져 있는 동안 항상 전류가 흘렀던 것과 대비됩니다.</p>

<h3>4.5 DC 스윕은 이전 점의 해에서 시작한다</h3>
<p>VTC를 그릴 때 솔버는 각 Vin에서 <b>직전 점의 해를 초기값</b>으로 Newton을 시작합니다. Vin = {k["newton_vin"]}일 때 Vout 초기값은 직전의 ≈ 1.8 V이고, 이 점에서 레슨 2와 같은 계산을 합니다. 이번에는 두 트랜지스터의 gds를 <b>더합니다</b>(병렬 저항).</p>
{eq("f(Vout) = Id_n + Id_p = 0    →    Vout_새 = Vout − f / (gdsn + gdsp)")}
{tbl(["반복", "Vout [V]", "Id,n [µA]", "Isd,p [µA]", "gds,n [µS]", "gds,p [µS]", "새 Vout [V]"], nrows)}
<p>2~3회에 수렴하고 값은 솔버의 {k["newton_solver"]:.6f} V와 일치합니다. 이 점에서 PMOS는 선형(Vsd ≈ 7.8 mV)이라 gds,p가 매우 커서(≈ 1.15 mS) 한 번에 거의 도착합니다. 반대로 Vout = 0.9 V에서 시작하면(PMOS 포화, gds가 작음) 접선이 거의 수평이라 Newton이 한 번에 <b>약 {over:.0f} V</b>로 튀어 나갑니다(전원 1.8 V를 훨씬 넘는 값). 그래서 작은 스텝으로 이전 해를 따라가는 방법이 중요합니다.</p>

<h3>4.6 과도 응답</h3>
{tbl(["항목", "값", "비고"], [
    ["tpHL / tpLH", f"{k['tphl']*1e12:.1f} ps / {k['tplh']*1e12:.1f} ps", f"βn = βp이므로 대칭 (레슨 3의 저항 부하는 내림 {d3['tp_fall']*1e12:.0f} ps, 올림 {d3['tp_rise']*1e12:.0f} ps)"],
    ["10–90 % 시간", f"내림 {k['fall_1090']*1e12:.0f} ps / 올림 {k['rise_1090']*1e12:.0f} ps", "CL = 20 fF"],
    ["한 주기 전원 에너지", f"{k['e_cycle']*1e15:.1f} fJ", f"C·Vdd² = {k['e_cv2']*1e15:.1f} fJ ({k['e_cycle']/k['e_cv2']*100-100:.0f} % 차이는 단락 전류)"],
    ["전원 전류 최대", f"{k['i_sc_tran_peak']*1e3:.2f} mA", "스위칭 순간에만 흐름 (그림 (f))"]])}
<p>출력이 0 → Vdd로 올라갈 때 전원이 CL을 충전하는 데 CL·Vdd²의 에너지를 쓰고, 그 절반은 PMOS에서 열이 됩니다. 이것이 CMOS의 동적 전력 <code>P = α·C·Vdd²·f</code>의 근거입니다.</p>
{box("ok", "요약", "<ul><li>PMOS는 NMOS의 부호 반전. 폭을 3배로 해서 β를 맞추면 대칭이 된다.</li><li>Vm = (Vdd−|Vtp|+√(βn/βp)·Vtn)/(1+√(βn/βp)), 이득 = (gmn+gmp)/(gdsn+gdsp).</li><li>정적 전류 ≈ 0, 전류는 스위칭 중에만 흐른다.</li></ul>")}
<p class="run">직접 해 보기: <code>python examples/lesson4_inverter.py</code></p></section>"""
    return s


# ---------------------------------------------------------------- lesson 5
def lesson5():
    k = J(5)
    trs = [[f"{r['vgs']:.1f}", f"{r['lv1']:.3e}" if r["lv1"] else "0", f"{r['ekv']:.3e}", f"{r['ic']:.3g}"] for r in k["table"]]
    sw = [[f"{x['n']}", f"{x['theory']:.2f}", f"{x['sim']:.2f}"] for x in k["swing"]]
    lk = [[f"{x['vt']:.1f}", f"{x['i_model']:.2e}", f"{x['i_supply']:.2e}"] for x in k["leak"]]
    s = head(5, "EKV 모델: 문턱 아래(subthreshold) 전류", "문턱 아래에서도 전류가 지수적으로 흐르는 것을 하나의 식으로 표현하는 EKV 모델을 이해하고, 약반전 전류를 손으로 계산해 본다.")
    s += f"""
<h3>5.1 Level 1의 빈틈</h3>
<p>Level 1은 Vgs &lt; Vth에서 Id = 0입니다. 실제 소자는 문턱 아래에서도 전류가 <b>지수적으로</b> 흐르고(약반전), 이 누설 전류가 현대 회로의 정적 전력을 좌우합니다. EKV 모델은 약반전에서 강반전까지 하나의 연속된 식으로 표현합니다.</p>
{eq("Id = Is · ( F(Vp − Vs) − F(Vp − Vd) ) · (1 + λ|Vds|)\nVp = (Vg − VTO)/n         Is = 2·n·β·Vt²         F(x) = ln²(1 + e^(x/2))        (모든 전압은 벌크 기준)")}
<p><code>Vt = kT/q</code> = {k["Vt"]*1e3:.3f} mV(27 °C), <code>n</code> = 1.3은 기울기 계수, <code>Is</code>는 특성 전류입니다. 이 소자에서 Is = 2·{k["n"]}·{k["beta"]*1e3:.4f}m·Vt² = <b>{k["Is"]*1e6:.4f} µA</b>입니다. F(x)는 x가 매우 음수이면 e^x, 매우 양수이면 (x/2)²에 가까워져서 두 영역을 매끄럽게 잇습니다. 드레인과 소스를 대칭으로 다루므로 레슨 1의 Vds &lt; 0 처리가 필요 없습니다.</p>
{fig("lesson5", "그림 5-1. (a) 시험 회로(레슨 1과 같고 model = EKV), (b) 약반전의 단면(채널이 거의 없고 전자가 확산으로 이동), (c) Id–Vgs 로그 그래프와 반전 영역 구분, (d) Vds 의존성, (e) 문턱 아래 기울기(swing), (f) 문턱전압과 누설 전류")}

<h3>5.2 손 계산: 약반전 전류</h3>
<p>x ≪ 0이면 F(x) ≈ e^x이므로 소스 쪽 항만 남아 Vs = 0, Vds가 충분히 크면</p>
{eq("Id ≈ Is · exp( (Vgs − VTO) / (n·Vt) ) · (1 + λVds)")}
<p>Vgs = 0.2 V, Vds = 1.8 V이면 exp((0.2−0.5)/(1.3·Vt)) = {k["weak_exp"]:.4e} → Id ≈ <b>{k["weak_hand"]*1e9:.4f} nA</b>, 코드는 <b>{k["weak_code"]*1e9:.4f} nA</b>입니다. 손 계산이 약 {(k["weak_hand"]/k["weak_code"]-1)*100:.1f} % 큰 이유는 F(x) ≈ e^x가 극한식이라 정확한 ln²(1+e^(x/2))보다 (1−e^(x/2)) 배, 즉 약 1.2 % 크기 때문입니다. 계산이 틀린 것이 아니라 근사의 크기입니다.</p>

<h3>5.3 Level 1과 EKV 비교 (Vds = 1.8 V, 포화)</h3>
{tbl(["Vgs [V]", "Level 1 Id [A]", "EKV Id [A]", "반전 계수 IC = Id/Is"], trs)}
<ul>
<li><b>IC &lt; 0.1: 약반전</b> (Vgs &lt; {k["vgs_ic01"]:.2f} V), <b>0.1 ~ 10: 중반전</b>, <b>IC &gt; 10: 강반전</b> (Vgs &gt; {k["vgs_ic10"]:.2f} V). Level 1은 Vth = 0.5 V 근처에서 절벽처럼 0이 되지만 EKV는 매끄럽게 이어집니다.</li>
<li>강반전에서는 EKV가 Level 1의 <b>1/n</b> 크기입니다. Vgs = 1.0 V, Vds = 1.8 V에서 EKV/Level 1 = <b>{k["strong_ratio"]:.3f}</b> (1/n = {1/k["n"]:.3f}). 같은 KP를 쓰면 EKV 전류가 작게 나오는 이유입니다(EKV의 포화 전류는 β·Vov²/(2n)).</li></ul>

<h3>5.4 문턱 아래 기울기와 Vds 의존성</h3>
<p>약반전에서 Id는 Vgs에 대해 지수이므로 로그 그래프에서 직선이고, Id를 10배 바꾸는 데 필요한 Vgs 변화가 <b>subthreshold swing</b> S = n·Vt·ln 10입니다.</p>
{tbl(["n", "이론 S [mV/decade]", "시뮬레이션 S [mV/decade]"], sw)}
<p>n = 1이 이상적인 한계(약 60 mV/decade)이고 n이 커질수록 게이트가 채널을 덜 제어합니다. 또한 약반전에서는 Id가 <code>(1 − e^(−Vds/Vt))</code>에 비례해서 Vds가 약 3·Vt에서 95 %에 도달합니다(그림 (d)): 이론 {k["vds_95_theory"]*1e3:.1f} mV, 시뮬레이션 {k["vds_95_weak"]*1e3:.1f} mV. 강반전의 포화 전압 Vov에 비해 훨씬 작습니다.</p>

<h3>5.5 회로에 미치는 영향: 누설 전류</h3>
<p>인버터에서 Vin = 0일 때 꺼진 NMOS의 약반전 전류가 정적 전류가 됩니다. 문턱전압을 낮추면 누설이 <b>지수적으로</b> 늘어납니다.</p>
{tbl(["Vth [V]", "모델 누설 전류 [A]", "솔버가 보고한 전원 전류 [A]"], lk)}
<p>Vth를 100 mV 낮출 때마다 누설이 약 <b>{k["leak_ratio_per_100mV"]:.1f}배</b> 늘어납니다(이론 e^(0.1/(n·Vt)) = {k["leak_ratio_theory"]:.1f}배). 마지막 열의 값은 모델 누설에 <b>gmin 바닥(≈ 3.6 pA)</b>이 더해진 것이라, 모델 누설이 수 pA 이하이면 솔버 결과는 gmin이 지배합니다. 아주 작은 누설을 다룰 때는 gmin을 낮추거나 소자 전류를 직접 읽어야 합니다.</p>
{box("warn", "한계", "<p>이 EKV는 장채널 단순형입니다. 이동도 저하, 속도 포화, 단채널 효과(DIBL, Vth roll-off)와 몸체 효과의 전압 의존성이 없습니다. 레슨 6의 전하 모델에서도 공핍 전하를 생략했습니다.</p>")}
{box("ok", "요약", "<ul><li>EKV는 F(x) = ln²(1+e^(x/2)) 하나로 약반전~강반전을 잇는다.</li><li>약반전: Id ≈ Is·e^((Vgs−VTO)/(nVt)), swing = n·Vt·ln10 (n=1.3이면 약 77 mV/dec).</li><li>Vth가 100 mV 낮으면 누설이 약 19배.</li></ul>")}
<p class="run">직접 해 보기: <code>python examples/lesson5_ekv.py</code></p></section>"""
    return s


# ---------------------------------------------------------------- lesson 6
def lesson6():
    k = J(6)
    h = k["hand"]
    cs = k["conservation"]
    fo, rg = k["fo1"], k["ring"]
    s = head(6, "채널 전하 모델: MOSFET 자신의 용량", "MOSFET이 전하를 저장한다는 것(Qg, Qd, Qs)과 그것이 지연에 미치는 영향을 이해하고, 교과서의 고전적인 값(½, ⅔, 0.4)을 코드로 확인한다.")
    s += f"""
<h3>6.1 왜 필요한가</h3>
<p>레슨 3·4의 지연은 외부 커패시터와 겹침(overlap) 용량만으로 계산한 값이라 <b>실제보다 낙관적</b>입니다. 실제 MOSFET은 채널의 반전 전하 때문에 게이트·소스·드레인 사이에 <b>바이어스에 따라 변하는 용량</b>을 갖습니다. 이것을 용량(C)이 아니라 <b>단자 전하 Q(V)</b>로 모델링해야 전하가 보존됩니다.</p>
{fig("lesson6", "그림 6-1. (a) 소자 내부 용량 Cgd, Cgs, (b) 채널 전하가 소스와 드레인으로 나뉨, (c) 용량 대 Vds, (d) C–V 곡선, (e) 단자 전하, (f) 링 오실레이터에 미치는 영향")}

<h3>6.2 전하는 어떻게 구하나 (EKV 전하 모델)</h3>
<p>각 채널 끝의 정규화 전하 밀도 q를 전류 변수에서 구합니다: <code>i = q² + q</code>, 즉 <code>q = (√(1+4i) − 1)/2</code>(소스 끝은 i = i_f, 드레인 끝은 i = i_r). 채널을 따라 q를 적분하면 총 반전 전하가 되고, 위치 y/L를 가중치로 적분하면 드레인에 귀속되는 몫이 됩니다(<b>Ward–Dutton 분배</b>). 나머지는 소스 몫이고, 게이트 전하는 반대 부호입니다.</p>
{eq("Q_I = −Q0·W·L·∫ q dy/L        Q0 = 2·n·Vt·Cox\nQg = −Q_I,   Qd = (드레인 몫),   Qs = Q_I − Qd,   Qb = 0   →   Qg + Qd + Qs + Qb = 0")}
<p>단자 용량은 전하의 전압 미분 <code>C_kj = ∂Q_k/∂V_j</code>로 얻고(수치 미분), 과도 해석에서는 레슨 3의 커패시터와 같은 방식(companion model)으로 매 스텝 <code>i_k = dQ_k/dt</code>를 넣습니다.</p>

<h3>6.3 손 계산 ① 총 반전 전하와 분배 (n = 1, Vgs = Vds = 1.8 V)</h3>
<p>Cox = εox/tox = {k["cox"]*1e3:.3f} mF/m² (tox = 4 nm), Cox·W·L = {k["cgn"]*1e15:.3f} fF (NMOS 1 µm), {k["cgp"]*1e15:.3f} fF (PMOS 3 µm). 강반전 포화의 고전적 결과는</p>
{eq("Q_I = −(2/3)·Cox·W·L·Vov,     Qd = 0.4·Q_I,     Qs = 0.6·Q_I")}
{tbl(["항목", "손 계산 (극한식)", "코드", "비고"], [
    ["총 반전 전하 |Q_I| (Vov = 1.3 V)", f"{h['qi_hand']*1e15:.4f} fC", f"{h['qg']*1e15:.4f} fC", f"코드가 {abs(h['qg']/h['qi_hand']-1)*100:.1f} % 작음: 유한한 반전 정도 보정"],
    ["드레인 몫 / 소스 몫", "40 % / 60 %", f"{h['split_d']*100:.1f} % / {h['split_s']*100:.1f} %", "Ward–Dutton 40/60"]])}
<p>손 계산이 약 {abs(h['qg']/h['qi_hand']-1)*100:.0f} % 큰 것은 극한식(q → ∞)이기 때문입니다. Vov = 1.3 V에서도 정규화 전하 q가 약 25라서 1/(2q) ≈ 2 % 안팎의 보정이 남는 것과 같은 크기입니다.</p>

<h3>6.4 손 계산 ② 고전적인 용량 값</h3>
<p>몸체 효과가 없는 경우(<b>n = 1</b>) 교과서의 값이 그대로 나옵니다(Cox·W·L 단위, Vgs = 1.8 V).</p>
{tbl(["조건", "Cgg", "Cgs", "Cgd", "교과서 값"], [
    ["Vds = 0 (선형)", f"{k['cap_vds0']['cgg']:.3f}", f"{k['cap_vds0']['cgs']:.3f}", f"{k['cap_vds0']['cgd']:.3f}", "1, ½, ½"],
    ["포화", f"{k['cap_sat']['cgg']:.3f}", f"{k['cap_sat']['cgs']:.3f}", f"{k['cap_sat']['cgd']:.3f}", "⅔, ⅔, 0"]])}
<p>포화에서 <b>Cgd = 0이지만 비대칭 전달 용량(transcapacitance)</b>이 있습니다: Cdg = ∂Qd/∂Vg = {k['cap_sat']['cdg']:.3f}, Csg = ∂Qs/∂Vg = {k['cap_sat']['csg']:.3f} (= −0.4·⅔, −0.6·⅔). 게이트가 오르면 채널 전하가 소스와 드레인에서 공급되기 때문입니다. 단자 전하로 모델링해야 이런 효과가 자연스럽게 들어옵니다. n = 1.3이면 소스·드레인 전위에 대한 미분이 n배가 되고 벌크 전하를 생략했기 때문에 Cgb가 음수로 나옵니다(아래 한계 참고).</p>

<h3>6.5 전하 보존 검증</h3>
<p>CMOS 인버터의 입력을 이상적인 전압원으로 0 → 1.8 V 구동하면, 전원이 게이트로 공급한 전하는 두 트랜지스터의 게이트 전하 변화의 합과 같아야 합니다.</p>
{tbl(["항목", "값"], [
    ["NMOS ΔQg", f"{cs['dq_n']*1e15:.3f} fC"], ["PMOS ΔQg", f"{cs['dq_p']*1e15:.3f} fC"],
    ["기대값 (합)", f"{cs['expected']*1e15:.3f} fC"], ["시뮬레이션에서 전원이 공급한 전하", f"<b>{cs['delivered']*1e15:.3f} fC</b>"]])}

<h3>6.6 지연에 미치는 영향</h3>
{tbl(["회로", "내부 전하 모델 없음", "있음", "비율"], [
    ["인버터 → 인버터 (FO1) tpHL", f"{fo['off']['tphl']*1e12:.1f} ps", f"{fo['on']['tphl']*1e12:.1f} ps", f"×{fo['on']['tphl']/fo['off']['tphl']:.2f}"],
    ["인버터 → 인버터 (FO1) tpLH", f"{fo['off']['tplh']*1e12:.1f} ps", f"{fo['on']['tplh']*1e12:.1f} ps", f"×{fo['on']['tplh']/fo['off']['tplh']:.2f}"],
    ["5단 링 오실레이터 주기", f"{rg['off']*1e12:.1f} ps", f"{rg['on']*1e12:.1f} ps", f"×{rg['ratio']:.2f}"]])}
<p>게이트 용량이 다음 단의 부하가 되므로 지연이 커집니다. 겹침 용량만 쓴 앞선 레슨의 지연은 이만큼 낙관적이었습니다.</p>

{box("warn", "개발 중에 잡은 오류 (검증이 왜 중요한가)", f'''<p>처음 구현에서는 링 오실레이터 주기가 용량을 넣었는데도 <b>144 ps에서 66 ps로 절반이 되어</b> 오히려 빨라졌습니다. 같은 위치에 선형 커패시터를 달아 비교한 기준(202~259 ps)이 있었기 때문에 이상하다는 것을 알 수 있었습니다. 원인은 <b>모델이 전하를 (g, d, s, b) 순서로 돌려주는데 솔버는 (d, g, s, b) 순서로 읽은 것</b>이어서, 게이트 전하가 드레인 노드에 연결되고 있었습니다. 수정 후 주기는 {rg["on"]*1e12:.1f} ps가 되어 두 기준 사이에 들어왔습니다.</p>
<p>더 큰 문제는 <b>당시의 용량 테스트가 모두 통과하고 있었다</b>는 점입니다. 용량은 10⁻¹⁴ F 수준인데 <code>pytest.approx</code>의 기본 절대 허용오차가 10⁻¹²라서, 어떤 값이 와도 통과하는 무의미한 테스트였습니다. 지금은 값을 Cox·W·L로 나눈 무차원 수로 비교하고, 옛 순서로 되돌리면 8개 테스트가 실패하는 것을 확인했습니다. 교훈: <b>테스트가 통과하는 것만으로는 부족하고, 테스트가 실제로 틀린 코드를 잡는지 확인해야 합니다.</b></p>''')}
{box("warn", "이 모델의 한계", "<ul><li>공핍·축적 전하(벌크 전하 Qb)를 모델링하지 않습니다. 그래서 Vth 아래에서 Cgg ≈ 0이고(실제로는 공핍 용량이 남음), n &gt; 1이면 Cgb가 음수가 됩니다.</li><li>용량 행렬은 수치 미분으로 구합니다(해석적 미분 아님).</li><li>ngspice Level 1은 Meyer 용량을 쓰므로 이 전하 모델과는 직접 비교할 수 없습니다. 레슨 7의 교차검증은 겹침 용량만 쓰는 Level 1로 했습니다.</li></ul>")}
{box("ok", "요약", "<ul><li>MOSFET은 단자 전하 Qg, Qd, Qs를 갖고 합이 항상 0이다.</li><li>포화에서 Cgs = ⅔·Cox·W·L, Cgd = 0, Qd : Qs = 40 : 60.</li><li>내부 용량은 지연을 크게 늘린다(링 주기 ×1.54).</li></ul>")}
<p class="run">직접 해 보기: <code>python examples/lesson6_charge.py</code></p></section>"""
    return s


# ---------------------------------------------------------------- lesson 7
def lesson7():
    k = J(7)
    t, r, v, c, o = k["tran"], k["ring"], k["vtc"], k["curves"], k["op"]
    s = head(7, "ngspice와 교차검증", "같은 netlist를 minispice와 ngspice에 넣고 결과를 비교해서, 우리 솔버가 맞다는 근거를 숫자로 확인한다.")
    s += f"""
<h3>7.1 방법</h3>
<p>검증은 <b>“같은 입력, 다른 구현”</b>을 비교하는 것입니다. 인버터와 링 오실레이터의 netlist 파일을 그대로 두 시뮬레이터에 넣습니다(ngspice에는 분석 카드를 빼고 <code>.control</code> 블록을 붙여서 결과를 파일로 저장). 비교 조건을 맞추기 위해 ngspice에는 <code>reltol=1e-6 abstol=1e-14 vntol=1e-9 gmin=1e-12 method=trap</code>과 시간 간격 상한(<code>tmax = tstep</code>)을 줍니다. 모델은 두 쪽 모두 <b>SPICE Level 1</b>이고 겹침 용량만 쓰도록 맞췄습니다. EKV와 전하 모델은 비교 대상에서 제외했습니다(ngspice에 같은 방정식의 내장 모델이 있는지는 확인하지 않았습니다).</p>
{fig("lesson7", "그림 7-1. (a) 한 netlist, 두 시뮬레이터, (b) 차이 요약, (c)~(f) 겹쳐 그린 결과 (선: minispice, ○: ngspice)")}
{code("""brew install ngspice          # ngspice 47 로 확인함
python examples/lesson7_ngspice.py""")}

<h3>7.2 결과 (ngspice {k["ngspice_version"]})</h3>
{tbl(["비교 항목", "최대 차이", "비고"], [
    ["동작점 Vd (레슨 2 회로)", f"{o['diff']:.1e} V", f"minispice {o['mini']:.9f} V / ngspice {o['ngspice']:.9f} V"],
    ["NMOS 출력 특성 5곡선 Id", f"{c['max_abs_diff']:.1e} A", f"최대 Id의 {c['rel']:.1e}배"],
    ["인버터 VTC Vout", f"{v['max_dv']*1e6:.2f} µV", f"기울기가 큰 구간에서는 Vin {v['max_equiv_vin_shift']*1e6:.2f} µV 어긋남에 해당. Vm {v['vm_mini']:.6f} V vs {v['vm_ng']:.6f} V"],
    ["인버터 과도 Vout", f"{t['max_dv']*1e3:.2f} mV", f"rms {t['rms_dv']*1e3:.2f} mV. tpHL {t['tphl_mini']*1e12:.2f} vs {t['tphl_ng']*1e12:.2f} ps, tpLH {t['tplh_mini']*1e12:.2f} vs {t['tplh_ng']*1e12:.2f} ps"],
    ["링 오실레이터 주기", f"{abs(r['period_mini']-r['period_ng'])*1e12:.2f} ps", f"{r['period_mini']*1e12:.2f} vs {r['period_ng']*1e12:.2f} ps ({r['rel']*100:.2f} %), 교차 횟수 {r['n_cross'][0]} = {r['n_cross'][1]}"]])}
<p>동작점과 출력 특성은 10⁻⁹~10⁻¹³ 수준으로 일치하고, VTC는 1 µV 이하(기울기가 큰 구간에서도 Vin 0.1 µV 어긋남에 해당), 과도 해석은 수 mV, 링 주기는 0.13 % 안쪽입니다.</p>

<h3>7.3 차이가 나는 이유와 의미</h3>
<ul>
<li><b>DC가 거의 완벽히 맞는 이유</b>: 같은 방정식(Level 1)과 같은 Newton 풀이이기 때문입니다. 이 일치는 모델 구현, MNA 조립, Newton 수렴이 모두 맞다는 강한 증거입니다.</li>
<li><b>과도 차이(최대 {t['max_dv']*1e3:.1f} mV)</b>: 가파른 에지에서 두 솔버의 시간 점 위치와 적분 방법 구현이 달라서 생기는 차이입니다. 전원 전류의 첨두값이 {t['ipeak_mini']*1e3:.3f} mA와 {t['ipeak_ng']*1e3:.3f} mA로 {abs(t['ipeak_mini']/t['ipeak_ng']-1)*100:.1f} % 다른 것도 같은 원인(가파른 순간을 어디서 샘플링하는가)으로 보이지만, 이 원인을 추가 실험으로 따로 확인하지는 않았습니다.</li>
<li><b>이 검증이 말해 주는 것</b>: Level 1 모델, DC·transient 솔버, 펄스 처리(breakpoint), Backward/trapezoidal 적분 중 trapezoidal이 ngspice와 맞는다는 것.</li>
<li><b>이 검증이 말해 주지 않는 것</b>: EKV 모델과 레슨 6의 전하 모델은 이번 비교에 넣지 않았습니다. 같은 방정식을 ngspice에서 돌리려면 레슨 8의 Verilog-A 경로가 필요합니다.</li></ul>
{box("ok", "요약", "<ul><li>같은 netlist, 다른 구현 비교가 솔버 검증의 기본이다.</li><li>Level 1에서 minispice는 ngspice와 동작점·출력 특성 10⁻⁹ 이하, VTC 1 µV 이하, 링 주기 0.13 % 안쪽으로 일치한다.</li><li>비교 조건(허용오차, gmin, 시간 간격)을 맞추는 것이 중요하다.</li></ul>")}
<p class="run">직접 해 보기: <code>python examples/lesson7_ngspice.py</code> (ngspice가 설치되어 있어야 함)</p></section>"""
    return s


# ---------------------------------------------------------------- lesson 8
def lesson8():
    va = (ROOT / "examples" / "va" / "ekv_simple.va").read_text()
    s = head(8, "Verilog-A와 OSDI: 실제 compact model 연결", "compact model을 Verilog-A로 쓰고 OpenVAF로 컴파일해서 ngspice에 연결하는 흐름을 이해한다.")
    s += f"""
{box("warn", "이 레슨의 실행 상태: 미실행", "<p>이 레슨의 절차는 <b>이 교재를 만든 환경에서 실행·검증하지 못했습니다.</b> ngspice 47이 OSDI를 지원하는 것(<code>pre_osdi</code> 명령 존재)까지만 확인했고, OpenVAF 컴파일과 ngspice 시뮬레이션은 실행하지 못했습니다. 아래 Verilog-A 파일은 <b>한 번도 컴파일되지 않았으므로</b> 문법 오류가 있을 수 있습니다. 직접 실행해서 확인하시기 바랍니다. 따라서 이 레슨에는 결과 숫자가 없습니다.</p>")}
<h3>8.1 왜 Verilog-A/OSDI인가</h3>
<p>레슨 1~6에서는 모델을 Python으로 직접 구현했습니다. 실제 공정의 compact model(BSIM-CMG, BSIM4 등)은 수천 줄의 수식이고, 보통 <b>Verilog-A</b>(아날로그 동작 기술 언어)로 배포됩니다. Verilog-A는 “단자 전압 → 전류·전하” 관계만 쓰면 도함수는 컴파일러가 자동으로 만들어 줍니다(레슨 1의 gm, gds를 손으로 미분할 필요가 없음). <b>OpenVAF</b>가 Verilog-A를 기계어로 컴파일해서 <b>OSDI</b>라는 표준 인터페이스의 공유 라이브러리(<code>.osdi</code>)로 만들면, ngspice 같은 시뮬레이터가 이를 불러와 소자로 씁니다.</p>
{fig("lesson8", "그림 8-1. (a) Verilog-A → OpenVAF → .osdi → ngspice 흐름(배지는 이 환경에서의 실행 상태), (b) OSDI 소자의 시험 회로")}

<h3>8.2 Python 모델과 Verilog-A의 대응</h3>
<p>레슨 5의 EKV를 그대로 옮긴 파일이 <code>examples/va/ekv_simple.va</code>입니다. 전류 부분은 한 줄씩 대응합니다(전하는 포함하지 않음).</p>
{tbl(["개념", "Python (minispice/models.py)", "Verilog-A (ekv_simple.va)"], [
    ["열전압 Vt", "<code>VT = 0.025865</code> (고정 상수)", "<code>vt = $vt;</code> (회로 온도에서 계산)"],
    ["극성 처리", "<code>pol * vd, ...</code>", "<code>TYPE * V(d, b)</code>"],
    ["핀치오프 전압", "<code>vp = (vgs − vbs − vto)/n</code>", "<code>vp = (vgb − TYPE*VTO)/N;</code>"],
    ["특성 전류 Is", "<code>2*n*kp*(w/l)*VT*VT</code>", "<code>i_s = 2.0*N*KP*(W/L)*vt*vt;</code>"],
    ["F(x) = ln²(1+e^(x/2))", "<code>_ekv_f(x)</code> (softplus)", "<code>spf*spf</code>, <code>spf = ln(1+exp(hf))</code>"],
    ["전류 출력", "<code>return i0*clm, gm, gds, gmb</code> (도함수 직접 계산)", "<code>I(d, s) &lt;+ TYPE*ids;</code> (도함수는 컴파일러가 생성)"]])}
{details("Verilog-A 소스 전체 보기", code(va))}

<h3>8.3 실행 절차 (직접 해 보실 부분)</h3>
{box("info", "OpenVAF 설치 시 주의", "<p>OpenVAF는 서드파티 실행 파일입니다. 공식 배포처에서 받아 <b>체크섬을 확인</b>하고, 저장소와 분리된 폴더에 두고 사용하세요. 이 교재의 저장소에는 컴파일러 바이너리를 넣지 않았습니다. 제가 확인한 GitHub 릴리스 중 macOS(Apple Silicon)용 빌드는 커뮤니티 포크(OpenVAF-Reloaded)에 있었습니다. 어느 배포판을 쓸지는 직접 판단하세요.</p>")}
{code("""# 1. Verilog-A -> OSDI  (바이너리 이름은 배포판마다 다름: openvaf 또는 openvaf-r)
openvaf-r examples/va/ekv_simple.va        # ekv_simple.osdi 생성

# 2. ngspice netlist 에서 라이브러리를 불러오고 소자를 N 으로 시작하는 이름으로 사용
#    (정확한 .model 문법은 ngspice 매뉴얼의 OSDI 절을 확인할 것)
.control
pre_osdi ekv_simple.osdi
.endc
.model nmod ekv_simple TYPE=1 VTO=0.5 KP=300u N=1.3 LAMBDA=0.05
N1 d g s b nmod W=1u L=0.18u""")}
<h3>8.4 해 보면 좋은 비교 (아직 하지 않음)</h3>
<ol><li>Id–Vgs를 로그 그래프로, minispice의 <code>EKV</code>와 ngspice+OSDI 결과를 겹쳐 그리기(약반전 포함).</li><li>같은 EKV NMOS/PMOS로 만든 인버터의 VTC 비교.</li><li>두 결과가 완전히 같지 않다면 차이의 원인 찾기. 예상되는 후보는 열전압 상수(Python은 고정값, Verilog-A는 <code>$vt</code>)와 gmin 처리의 차이지만, 어느 쪽이 실제 원인인지는 실행해 봐야 압니다.</li></ol>
<p>이 비교가 통과하면 같은 방정식의 서로 다른 구현이 일치한다는 뜻이고, 이어서 공개된 실제 모델(예: BSIM-CMG의 Verilog-A)을 같은 방식으로 불러오는 것이 다음 단계입니다.</p>
{box("ok", "요약", "<ul><li>Verilog-A는 전압→전류·전하 관계만 쓰고, 도함수는 컴파일러가 만든다.</li><li>OpenVAF가 .osdi로 컴파일하고, ngspice가 <code>pre_osdi</code>로 불러 N 소자로 쓴다.</li><li>이 레슨의 실행은 아직 검증되지 않았다.</li></ul>")}</section>"""
    return s


# ---------------------------------------------------------------- recommended resources
def _a(url, text):
    return f'<a href="{url}" target="_blank" rel="noopener noreferrer">{text}</a>'


def resources():
    ok, mem, unk = "검색으로 확인", "저자의 기억(검색에서는 확인 못 함)", "내용 미확인"
    books = [
        ["<b>The SPICE Book</b><br>Andrei Vladimirescu (Wiley)", "SPICE 개발에 참여한 저자의 책. 시뮬레이션 알고리즘과 장치 모델 부록. 레슨 2~3과 연결", ok],
        ["<b>Operation and Modeling of the MOS Transistor</b><br>Yannis Tsividis, Colin McAndrew", "MOSFET 물리와 모델링(전하 모델 포함)의 표준 교재로 알려져 있음", mem],
        ["<b>Charge-Based MOS Transistor Modeling: The EKV Model for Low-Power and RF IC Design</b><br>Christian Enz, Eric Vittoz (Wiley)", "EKV를 가장 자세히 다룬 책. 레슨 5~6의 다음 단계", ok],
        ["<b>MOSFET Models for SPICE Simulation, Including BSIM3v3 and BSIM4</b><br>William Liu", "실제 산업 모델(BSIM)을 공부할 때", ok],
        ["<b>Compact MOSFET Models for VLSI Design</b><br>A. B. Bhattacharyya", "EKV, BSIM, PSP와 전하 기반 모델링을 두루 다룸", "검색 결과에 언급됨"],
        ["<b>Inside SPICE</b><br>Ron Kielkowski", "제목상 SPICE 내부 알고리즘을 다루는 책", unk]]
    videos = [
        [_a("https://classcentral.com/classroom/youtube-semiconductor-device-modeling-47521", "NPTEL (IIT Madras) “Semiconductor Device Modeling”"),
         "MOSFET의 DC 모델, 문턱전압과 표면 전위 기반 해, 파라미터 추출, 소형화 효과. 이 교재의 주제와 가장 가까움 (YouTube 재생목록을 Class Central이 정리한 페이지)"],
        [_a("https://ngspice.sourceforge.io/tutorials.html", "ngspice 공식 튜토리얼 목록"),
         "IISc Bangalore 입문 영상, Tom Anderson의 시뮬레이션 시리즈, KiCad와 ngspice 시연 채널 등 YouTube 링크 모음. 개별 영상의 품질은 직접 확인"],
        [_a("https://github.com/benedictjones/engineeringthings-pyspice", "PySpice 영상 시리즈 (작성자 GitHub)"), "Python으로 ngspice를 돌리는 방법"],
        [_a("https://graphsearch.epfl.ch/en/concept/40345/lectures", "EPFL의 EKV 모델 강의 목록"), "YouTube 영상인지는 확인하지 못함"],
        [_a("https://hasler.ece.gatech.edu/Courses/ECE4430/Proj1/index.html", "Georgia Tech ECE4430 MOSFET 모델링 과제 페이지"),
         "EKV SPICE 모델 추출 자료와 Brad Minch, Ali Hajimiri 강의 링크"]]
    s = '<section id="resources" class="plain"><h2><span class="num">+</span>추천 자료: 책과 강의</h2>'
    s += "<p>이 교재 다음 단계를 위한 자료입니다. 레슨 순서로 보면 <b>레슨 2~3(알고리즘)</b>은 The SPICE Book, <b>레슨 1·5·6(MOSFET 모델)</b>은 Tsividis 책과 Enz·Vittoz 책, <b>레슨 7~8(ngspice, OSDI)</b>은 ngspice 공식 문서가 맞습니다.</p>"
    s += "<h3>책</h3>" + tbl(["책", "어디에 좋은가", "이 목록을 만들 때의 확인 수준"], books)
    s += ("<p>책은 저작권 문제로 링크를 달지 않았습니다. 무료 자료로는 " + _a("https://ngspice.sourceforge.io/ngspice-tutorial.html", "ngspice 공식 초보자 튜토리얼")
          + "과 ngspice 매뉴얼(OSDI 절 포함)이 있습니다.</p>")
    s += "<h3>강의와 영상</h3>" + tbl(["자료", "설명"], videos)
    s += box("warn", "확인하지 못한 것", "<ul><li>위 링크는 웹 검색으로 찾은 것이고 <b>YouTube 영상을 직접 열어 보지는 못했습니다.</b> 지금도 재생되는지, 어떤 언어인지(대부분 영어) 확인해 보세요.</li>"
                    "<li><b>한국어 SPICE·MOSFET 모델링 YouTube 채널은 검색으로 찾지 못했습니다.</b> 채널 이름을 지어내지 않았습니다. “BSIM 모델 강의”, “반도체 소자 SPICE 모델링”, “LTspice MOSFET 시뮬레이션” 같은 검색어로 직접 찾아보세요.</li>"
                    "<li>목록 작성일: 2026-11-19. 자료의 가용성은 시간이 지나면 달라집니다.</li></ul>")
    s += "</section>"
    return s


# ---------------------------------------------------------------- lessons 9 and 10: FinFET and GAA
def _srcs(items):
    return "<ul class=\"src\">" + "".join(f"<li>{_a(u, t)}</li>" for u, t in items) + "</ul>"


SRC_BSIM = [("https://bsim.gitbooks.io/bsimcmg/content/Ch5.1.1.html", "BSIM-CMG 매뉴얼 5.1.1 (GEOMOD 파라미터)"),
            ("https://bsim.gitbooks.io/bsimcmg/content/Ch3.1.2.html", "BSIM-CMG 매뉴얼 3.1.2 (유효 폭, 채널 길이, fin 수)")]
SRC_LEC = ("https://people.eecs.berkeley.edu/~tking/presentations/KingLiu_SOI2012.pdf", "Berkeley 강의자료 (T.-J. K. Liu, SOI 2012): 슬라이드 7, 26")
SRC_WEFF = [("https://semiwiki.com/?p=1180", "SemiWiki: FinFET 폭 증분에 대한 설명"),
            ("https://sites.ji.sjtu.edu.cn/xinfei-guo/wp-content/uploads/sites/27/2021/05/pdf.pdf", "강의 자료: 폭 n(2H + t)")]

CHIP = {"fact": '<span class="st ok">확인된 사실</span>', "calc": '<span class="st part">코드로 계산</span>', "illus": '<span class="st no">교육용 예시값</span>'}


def lesson9():
    k = J(9)
    g, m = k["geom"], k["model"]
    S = m["sets"]
    import math as _m
    from minispice.models import VT as _VT
    beta = 300e-6 * (1e-6 / 20e-9)

    def ioff_hand(n, eta):
        return 2 * n * beta * _VT**2 * _m.exp((eta * m["vdd"] - m["vto"]) / (n * _VT)) * (1 + 0.05 * m["vdd"])
    rows = [[r["n"], f"{r['weff']:.0f} nm", f"{r['planar']:.0f} nm"] for r in g["rows"]]
    # Ioff: hand formula vs simulation, and the size of the F(x) ~ e^x correction that explains the gap
    ioff_err = {nm: v["ioff"] / ioff_hand(v["n"], v["eta"]) - 1 for nm, v in S.items()}
    ioff_corr = {nm: -_m.exp((v["eta"] * m["vdd"] - m["vto"]) / (v["n"] * _VT) / 2) for nm, v in S.items()}
    ss_err_max = max(abs(v["ss_sim"] / v["ss_hand"] - 1) for v in S.values())
    rl = k["rules"]
    rrows = [[f"{L:g} nm", f"{u:g} nm", f"{f:g} nm"] for L, u, f in zip(rl["L"], rl["utb"], rl["fin"])]
    mrows = [[nm, f"{v['n']}", f"{v['eta']}", f"{v['ss_hand']:.1f}", f"{v['ss_sim']:.1f}", f"{v['dibl_hand']:.0f}", f"{v['dibl_sim']:.1f}",
              f"{ioff_hand(v['n'], v['eta']):.2e}", f"{v['ioff']:.2e}"] for nm, v in S.items()]
    s = head(9, "FinFET: 구조에서 compact model 파라미터까지", "게이트가 채널의 여러 면을 감싸면 왜 좋은지 이해하고, FinFET의 구조(fin 높이·폭·개수)가 compact model의 파라미터(유효 폭 W, 기울기 계수 n, DIBL 계수 η)로 어떻게 바뀌는지 계산해 본다.")
    s += f"""
{box("warn", "이 레슨의 성격: 무엇이 사실이고 무엇이 예시인가", f'''<p>이 레슨의 값은 세 종류이고, 본문에서 아래 표시로 구분합니다.</p>
<ul><li>{CHIP["fact"]} 웹 검색으로 출처를 확인한 내용(유효 폭 공식, Intel 22 nm의 fin 피치·높이, Berkeley 강의의 설계 경험칙, BSIM-CMG의 구조 구분).</li>
<li>{CHIP["calc"]} minispice로 계산한 값. 손 계산과 시뮬레이션을 비교합니다.</li>
<li>{CHIP["illus"]} <b>제가 정한 가상의 값</b>(fin 폭 8 nm, 모델 파라미터 n·η). 어떤 공정에서 추출한 값이 아니므로 <b>크기가 아니라 방향(순서)과 원리</b>를 보는 데 쓰세요.</li></ul>
<p>또 이 교재의 모델은 BSIM-CMG가 아니며(레슨 8은 아직 실행되지 않았습니다), <b>정전기적 자연 길이(natural length)의 정확한 공식은 원문으로 확인하지 못해서 쓰지 않았습니다.</b></p>''')}

<h3>9.1 왜 FinFET인가</h3>
<p>평면형은 게이트가 채널 <b>위쪽 한 면</b>만 덮습니다. 게이트 길이 L이 짧아지면 드레인 전압이 채널 아래쪽 장벽을 낮추는 것(<b>DIBL</b>)을 게이트가 막지 못하고, 문턱 아래 기울기도 나빠져서 꺼진 상태의 누설이 커집니다. 해법은 <b>게이트와 채널의 용량성 결합을 키우는 것</b>, 즉 채널을 얇게 세우고 게이트가 여러 면을 감싸게 하는 것입니다. Berkeley 강의자료도 “게이트와 채널의 결합이 클수록 채널 전위를 더 잘 제어하고, DIBL이 줄어든다”고 설명합니다. {CHIP["fact"]}</p>
{fig("lesson9", "그림 9-1. (a) FinFET 3차원 구조, (b) 채널에 수직인 단면(점선 = 게이트가 닿는 면), (c) 시험 회로와 netlist, (d) fin 수에 따른 유효 폭, (e) DIBL 100 mV/V에 필요한 몸체 크기, (f) 모델의 Id–Vgs (예시 파라미터)")}

<h3>9.2 구조 읽기</h3>
<ul><li><b>fin</b>: 기판 위에 세운 얇은 실리콘 벽입니다. 높이 H, 폭 W. 한 트랜지스터는 fin을 n개 나란히 둘 수 있습니다.</li>
<li><b>게이트</b>가 fin을 위와 양옆 <b>3면</b>에서 감쌉니다(그림 (b)의 점선). 평면형은 윗면 하나입니다.</li>
<li>소스와 드레인은 fin의 양 끝입니다(그림 (a)의 주황색). 전류는 fin 안을 소스에서 드레인으로 흐릅니다.</li></ul>

<h3>9.3 손 계산 ① 유효 채널 폭 {CHIP["fact"]}{CHIP["calc"]}</h3>
<p>전류가 흐르는 폭은 게이트가 닿는 면의 길이입니다. fin 하나당 양옆 2H와 윗면 W를 더한 값이고, fin이 n개면 n배입니다.</p>
{eq("W_eff = n · (2·H + W_fin)")}
<p>H = {g["h"]:.0f} nm, fin 피치 = {g["pitch"]:.0f} nm는 Intel 22 nm 세대 값으로 2차 자료에서 확인했고(1차 출처로 재확인 필요), <b>fin 폭 W_fin = {g["wfin"]:.0f} nm는 제가 가정한 값</b>입니다{CHIP["illus"]}. 그러면 fin 하나당 2·{g["h"]:.0f} + {g["wfin"]:.0f} = <b>{g["weff_fin"]:.0f} nm</b>이고, 같은 레이아웃 폭(피치 {g["pitch"]:.0f} nm)에 놓인 평면형의 폭 {g["pitch"]:.0f} nm보다 <b>×{g["ratio_vs_planar"]:.2f}</b> 큽니다.</p>
{tbl(["fin 수 n", "FinFET의 W_eff", "같은 풋프린트의 평면형 W"], rows)}
<p><b>폭 양자화</b>: 폭은 fin 개수 단위로만 바뀝니다(그림 (d)의 계단). 그래서 NMOS와 PMOS의 구동 세기 비율도 fin 개수의 비로 맞춰야 합니다. 참고로 실제로는 fin을 2개 단위로 늘리는 경우도 있다고 하며, 위의 단순한 식이 무시하는 효과도 있습니다(SemiWiki 글). 이 교재의 식은 가장 단순한 형태입니다.</p>

<h3>9.4 몸체 크기와 게이트 길이: 설계 경험칙 {CHIP["fact"]}</h3>
<p>Berkeley 강의자료(슬라이드 26, Yang·Fossum 논문 인용)는 <b>DIBL = 100 mV/V를 얻기 위해 필요한 몸체 크기</b>를 게이트 길이 L에 대한 비율로 정리합니다(Tox = 1.1 nm).</p>
{tbl(["구조", "필요한 몸체 크기"], [["초박막 평면형(UTB)", "t_Si ≈ L/5"], ["FinFET (좁은 fin)", "W_Si ≈ L/2"], ["트라이게이트(완화)", "W_Si &gt; L/2, H_Si &gt; L/5"]])}
{tbl(["L", "UTB 평면형 t_Si", "FinFET W_fin"], rrows)}
<p>같은 DIBL을 얻는 데 FinFET은 평면 초박막보다 <b>2.5배 두꺼운 몸체</b>를 허용합니다(L/2 대 L/5). 제조하기 훨씬 쉽다는 뜻입니다. 반대로 L이 10 nm이면 fin 폭이 5 nm 수준이어야 해서 FinFET도 결국 한계에 다가갑니다(레슨 10).</p>

<h3>9.5 compact model로 번역하기 {CHIP["calc"]}{CHIP["illus"]}</h3>
<p>구조의 장점은 compact model에서 두 파라미터로 나타납니다.</p>
{tbl(["물리", "파라미터", "식"], [
    ["게이트가 채널을 잘 제어한다 → 문턱 아래 기울기가 가파르다", "기울기 계수 <b>n</b> (이상값 1)", "SS = n·Vt·ln 10"],
    ["드레인 전압이 장벽을 덜 낮춘다", "DIBL 계수 <b>η</b> [V/V]", "Vth,eff = Vth − η·Vds"],
    ["채널 폭", "W", "W = n_fin·(2H + W_fin)"]])}
<p>minispice의 EKV에 DIBL을 넣었습니다. 게이트 전압을 <code>Vgs + η·Vds</code>로 바꾸는 것이 전부이고, 연쇄 법칙에 따라 <code>gds</code>에 <code>η·gm</code>이 더해집니다. (이 변경은 도함수 유한차분 검사와 “DIBL이 문턱을 η·Vds만큼 옮긴다” 검사를 통과합니다.)</p>
<p>아래 파라미터는 <b>가상의 예시값</b>입니다(L = 20 nm, Vdd = 0.8 V, VTO = {m["vto"]} V, W/L = 50). 게이트가 감싸는 면이 늘수록 n과 η가 작아지는 <b>방향</b>을 보여 줍니다.</p>
{tbl(["구조", "n", "η", "SS 손 [mV/dec]", "SS 시뮬", "DIBL 손 [mV/V]", "DIBL 시뮬", "Ioff 손 [A]", "Ioff 시뮬 [A]"], mrows)}
<ul>
<li><b>SS</b> 손 계산은 n·Vt·ln10이고, Vgs = 0~0.1 V(깊은 약반전)에서 측정한 시뮬레이션과 최대 {ss_err_max*100:.1f}% 차이입니다.</li>
<li><b>DIBL</b> 시뮬레이션은 같은 전류가 되는 Vgs를 Vds = 0.1 V와 0.8 V에서 비교해 추출했습니다. 설정값 η보다 3~4 mV/V 큰 것은 낮은 Vds에서 <code>(1 − e^(−Vds/Vt))</code>가 1이 아니고(0.98), 채널 길이 변조 항도 있기 때문입니다.</li>
<li><b>Ioff</b> 손 계산은 <code>Is·exp((η·Vds − VTO)/(n·Vt))·(1+λVds)</code>입니다. 시뮬레이션이 평면형은 {-ioff_err['planar']*100:.2f}%, FinFET은 {-ioff_err['FinFET']*100:.2f}% 작은데, 이는 레슨 5에서 본 <code>F(x) ≈ e^x</code> 근사의 보정 −e^(x/2)가 예측하는 {-ioff_corr['planar']*100:.2f}%, {-ioff_corr['FinFET']*100:.2f}%와 거의 같습니다.</li>
<li>결과적으로 같은 VTO에서 <b>꺼진 전류가 평면형이 FinFET의 약 {m["ioff_ratio"]:.0f}배</b>입니다(그림 (f)). n과 η가 모두 기여합니다. 켜진 전류는 거의 비슷합니다.</li></ul>

<h3>9.6 실제 compact model은 어떻게 다루나 {CHIP["fact"]}</h3>
<p>산업 표준으로 알려진 <b>BSIM-CMG</b>는 공통 다중 게이트 모델이고, <code>GEOMOD</code> 파라미터로 구조를 고릅니다: <b>0 = 이중 게이트, 1 = 트라이게이트, 2 = 사중 게이트, 3 = 원통형</b>. fin 폭과 높이, 채널 길이, fin 수를 입력으로 받습니다. 이 교재의 모델에는 없는 것도 많습니다: 3차원 정전기 효과, 양자 구속, 이동도의 전계 의존성, 기생 저항·용량 등입니다. 이런 모델을 ngspice에서 쓰려면 레슨 8의 경로(Verilog-A → OSDI)가 필요합니다.</p>
{box("warn", "이 레슨의 한계", "<ul><li>n, η, fin 폭은 예시이고 어떤 공정과도 맞춘 값이 아닙니다. 절대 수치(예: ×40배)를 실제 소자의 값으로 읽으면 안 됩니다.</li><li>L에 따른 DIBL·SS의 변화를 모델링하려면 자연 길이 이론이 필요한데, 정확한 식을 확인하지 못해서 다루지 않았습니다.</li><li>레슨 6의 전하 모델은 이 레슨에서 쓰지 않았고, FinFET 고유의 게이트-소스/드레인 기생 용량도 없습니다.</li></ul>")}
{box("ok", "요약", "<ul><li>FinFET은 게이트가 fin을 3면에서 감싸 채널 제어를 높인다. 유효 폭은 n·(2H + W_fin)이고 fin 개수 단위로만 바뀐다.</li><li>같은 DIBL에서 FinFET은 평면 초박막보다 몸체를 약 2.5배 두껍게 만들 수 있다(경험칙).</li><li>compact model에서는 n(문턱 아래 기울기)과 η(DIBL)가 작아지고 W가 n_fin·W_eff가 된다.</li></ul>")}
<h3>출처</h3>
{_srcs([SRC_LEC] + SRC_BSIM + SRC_WEFF)}
<p class="run">직접 해 보기: <code>python examples/lesson9_finfet.py</code></p></section>"""
    return s


def lesson10():
    k = J(10)
    g, S = k["geom"], k["sets"]
    gain = k["ion_gain_vs_planar"]
    rows = [[nm, f"{v['n']}", f"{v['eta']}", f"{v['ss_hand']:.1f} / {v['ss_sim']:.1f}", f"{v['dibl_hand']:.0f} / {v['dibl_sim']:.1f}",
             f"{v['vto_at_target']:.3f} V", f"{v['ion_at_target']*1e3:.2f} mA (×{gain[nm]:.2f})", f"{v['gain_hand']:.1f} / {v['gain_num']:.1f}"] for nm, v in S.items()]
    s = head(10, "GAA와 나노시트: 게이트가 채널을 완전히 감싼다", "FinFET의 한계가 왜 생기는지, 게이트가 4면을 감싸는 GAA(nanosheet)가 어떻게 이를 푸는지 이해하고, 게이트 제어가 좋아지면 회로 특성(Ion–Ioff, 이득)이 어떻게 달라지는지 계산해 본다.")
    s += f"""
{box("warn", "이 레슨의 성격", f'''<p>레슨 9와 같습니다. {CHIP["fact"]}(BSIM-CMG의 구조 구분, 원통형 유효 폭 π·D, 업계 동향), {CHIP["calc"]}(minispice 계산), {CHIP["illus"]}(나노시트 치수와 모델 파라미터 n, η)를 구분해서 표시합니다. 파라미터는 가상의 값이라 <b>순서와 원리</b>를 보는 용도입니다.</p>''')}
<h3>10.1 FinFET의 다음 단계</h3>
<p>레슨 9의 경험칙에 따르면 FinFET은 W_fin ≈ L/2가 필요합니다. L이 10 nm이면 fin 폭이 5 nm여야 하고, fin을 이렇게 얇고 높게 세우는 것은 점점 어렵습니다. 게이트가 3면이 아니라 <b>4면(전방위)</b>을 감싸면 같은 몸체 두께에서 채널 제어가 더 좋아집니다. 이것이 <b>GAA(gate-all-around)</b>이고, 실리콘을 얇은 판(<b>나노시트</b>) 여러 장으로 수평 적층하거나 가는 원통(나노와이어)으로 만듭니다.</p>
<p>업계 동향은 2차 자료로만 확인했습니다. 삼성이 2022년에 “3 nm” GAA 공정의 초기 생산을 시작했다고 보도되었고, TSMC의 N2도 나노시트를 쓰는 것으로 알려져 있습니다. 시기는 자료마다 다르고 현재의 양산 상태는 확인하지 못했으니 1차 출처로 확인하세요.</p>
{fig("lesson10", "그림 10-1. (a) 나노시트 GAA 3차원 구조, (b) FinFET과 나노시트의 단면 비교, (c) 유효 폭: fin은 계단식, 나노시트는 연속, (d) Ion–Ioff 곡선, (e) 인버터 VTC, (f) 게이트가 감싸는 면과 n, η")}

<h3>10.2 손 계산 ① 나노시트의 유효 폭 {CHIP["calc"]}{CHIP["illus"]}</h3>
<p>게이트가 직사각형 시트를 완전히 감싸면 시트의 <b>둘레 전체</b>가 채널이 됩니다. 폭 W, 두께 T인 시트 한 장의 유효 폭은 2(W + T)이고, N장이면 N배입니다. (이 식은 기하학에서 유도한 것이고 특정 문헌에서 인용한 공식이 아닙니다.)</p>
{eq("W_eff = N · 2 · (W + T)")}
<p>가상의 치수 W = {g["w"]:.0f} nm, T = {g["t"]:.0f} nm, N = {g["n"]}이면 시트 하나당 2·({g["w"]:.0f} + {g["t"]:.0f}) = <b>{g["per_sheet"]:.0f} nm</b>, 전체 <b>{g["weff_ns"]:.0f} nm</b>입니다. 윗면에만 게이트가 있다면 {g["top_only"]:.0f} nm뿐이므로, <b>감싸는 면이 폭을 만듭니다.</b> 원통형 나노와이어는 둘레 π·D이고(BSIM-CMG 매뉴얼에서 확인 {CHIP["fact"]}), 지름 6 nm이면 {g["cyl_weff"]:.1f} nm입니다. FinFET의 fin 하나({g["weff_fin"]:.0f} nm)와 비교하면 그림 (c)처럼 FinFET은 계단이고 나노시트는 시트 폭 W를 바꿔서 폭을 <b>연속적으로</b> 조절할 수 있습니다.</p>

<h3>10.3 손 계산 ② 게이트 제어가 회로에 주는 효과 {CHIP["calc"]}{CHIP["illus"]}</h3>
<p>레슨 9의 방식으로 세 구조의 파라미터를 가정했습니다(L = 20 nm, Vdd = 0.8 V, W/L = 50). 게이트가 감싸는 면이 1 → 3 → 4면으로 늘수록 n과 η가 작아집니다.</p>
{tbl(["구조", "n", "η", "SS 손/시뮬 [mV/dec]", "DIBL 손/시뮬 [mV/V]", "Ioff = 1 nA에 필요한 VTO", "그 때의 Ion", "인버터 이득 손/수치"], rows)}
<ul>
<li><b>같은 Ioff에서의 Ion</b>: 꺼진 전류가 같도록 문턱전압을 맞추면, n과 η가 작은 구조는 문턱전압을 더 낮출 수 있어서(VTO가 {S['planar']['vto_at_target']:.3f} → {S['FinFET']['vto_at_target']:.3f} → {S['GAA']['vto_at_target']:.3f} V) 켜진 전류가 커집니다. 여기에 EKV의 강반전 전류가 1/n에 비례하는 효과(레슨 5)도 더해집니다. 이 크기(×{gain["FinFET"]:.2f}, ×{gain["GAA"]:.2f})는 <b>가정한 n, η의 결과이므로 방향으로만 읽어야 합니다.</b></li>
<li><b>인버터 이득</b>: DIBL은 포화 영역의 출력 컨덕턴스를 키웁니다(<code>gds = λ·I + η·gm</code>). 그래서 gm/gds는 대략 1/η를 넘을 수 없습니다(η = 0.10, 0.04, 0.02이면 상한 10, 25, 50). 이득은 (gmn + gmp)/(gdsn + gdsp)로 손 계산한 값과 VTC의 최대 기울기가 같습니다(표의 마지막 열). η = 0.10이면 이득이 약 10, η = 0.02이면 약 44입니다. 그림 (e)의 VTC가 점점 가팔라지는 이유입니다.</li></ul>

<h3>10.4 BSIM-CMG에서의 구분 {CHIP["fact"]}</h3>
{tbl(["GEOMOD", "의미 (매뉴얼에서 확인)", "게이트가 감싸는 면 (일반 지식)"], [
    ["0", "이중 게이트", "양옆 2면"], ["1", "트라이게이트", "3면"], ["2", "사중 게이트", "4면 (정사각형 단면 GAA)"], ["3", "원통형 게이트", "전방위 (나노와이어)"]])}
<p>FinFET은 보통 이중/트라이게이트, GAA는 사중/원통형에 해당한다고 이해하면 되지만, 이것은 개념적 대응이고 <b>구조별 권장 설정을 매뉴얼에서 확인하지는 않았습니다.</b> GEOMOD 0~3의 의미와 원통형 유효 폭은 BSIM-CMG 매뉴얼에서 확인했습니다. 나노시트를 이 중 어느 설정으로 다루는지는 확인하지 못했습니다(나노시트를 위한 통합 모델 논문이 별도로 있다고만 확인). 실제로 쓰려면 매뉴얼을 직접 보세요.</p>
{box("warn", "이 레슨의 한계", "<ul><li>나노시트 치수와 n, η는 모두 가상의 값입니다. “GAA가 평면형의 2배 이상”처럼 읽으면 안 됩니다.</li><li>이 모델에 없는 것: 시트 사이 결합, 양자 구속, 자기 발열, 기생 저항·용량, 변동성 등.</li><li>L 의존성(자연 길이 이론)은 정확한 공식을 확인하지 못해 다루지 않았습니다.</li></ul>")}
{box("ok", "요약", "<ul><li>GAA는 게이트가 채널을 4면(전방위)에서 감싸 FinFET보다 짧은 L에서도 채널 제어를 유지한다.</li><li>나노시트의 유효 폭은 N·2(W + T)(기하 유도)이고 시트 폭으로 연속 조절된다. fin은 개수 단위로만 바뀐다.</li><li>게이트 제어가 좋으면(n, η 작음) 같은 누설에서 더 큰 Ion, 더 높은 이득을 얻는다(방향).</li></ul>")}
<h3>출처</h3>
{_srcs([SRC_LEC] + SRC_BSIM)}
<p class="run">직접 해 보기: <code>python examples/lesson10_gaa.py</code></p></section>"""
    return s
