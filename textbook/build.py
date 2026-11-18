"""Build docs/index.html: runs every lesson script and the test-suite, then assembles one self-contained page.

    python textbook/build.py            # run everything, then build
    python textbook/build.py --no-run   # only assemble from the existing examples/out files
"""

import datetime
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import lessons  # noqa: E402

SCRIPTS = ["lesson1_single_mosfet.py", "lesson2_newton.py", "lesson3_transient.py", "lesson4_inverter.py",
           "lesson5_ekv.py", "lesson6_charge.py", "lesson7_ngspice.py", "lesson8_osdi.py"]


def run_all():
    py = sys.executable
    for name in SCRIPTS:
        print("running", name, flush=True)
        r = subprocess.run([py, name], cwd=ROOT / "examples", capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit(f"{name} failed:\n{r.stderr[-1500:]}")


def run_tests():
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"], cwd=ROOT, capture_output=True, text=True)
    last = [l for l in r.stdout.strip().splitlines() if l.strip()][-1]
    m = re.search(r"(\d+) passed", last)
    f = re.search(r"(\d+) failed", last)
    return (int(m.group(1)) if m else 0), (int(f.group(1)) if f else 0)


CSS = """
:root{--bg:#fbfbf9;--fg:#1d2330;--mut:#5b6475;--line:#dfe3ea;--card:#fff;--acc:#1f3b73;--acc2:#b03a00;--code:#f3f4f7;
--ok:#e7f5ea;--okb:#2d7a3e;--warn:#fff3e0;--warnb:#b86a00;--info:#e8f0fe;--infob:#2a5bd7;--no:#fde8e8;--nob:#b3261e}
@media (prefers-color-scheme:dark){:root{--bg:#14171d;--fg:#e6e9ef;--mut:#9aa3b2;--line:#2a3140;--card:#1b2029;--acc:#8fb0ff;--acc2:#ff9a5c;--code:#1f2530;
--ok:#16301d;--okb:#6fcf86;--warn:#33270f;--warnb:#f0b35a;--info:#17233f;--infob:#8fb0ff;--no:#3a1816;--nob:#ff8b82}}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:64px}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.75 -apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Noto Sans KR","Malgun Gothic",system-ui,sans-serif}
.hero{padding:44px 20px 28px;max-width:1120px;margin:0 auto}
.hero h1{font-size:clamp(1.6rem,4vw,2.3rem);line-height:1.3;margin:0 0 8px;color:var(--acc)}
.hero p{margin:.3rem 0;color:var(--mut);max-width:760px}
nav.toc{position:sticky;top:0;z-index:10;background:color-mix(in srgb,var(--bg) 92%,transparent);backdrop-filter:blur(8px);border-bottom:1px solid var(--line)}
nav.toc ul{list-style:none;margin:0 auto;padding:8px 16px;max-width:1120px;display:flex;gap:6px;flex-wrap:wrap}
nav.toc a{display:inline-block;padding:3px 10px;border:1px solid var(--line);border-radius:999px;color:var(--fg);text-decoration:none;font-size:.88rem;background:var(--card)}
nav.toc a:hover{border-color:var(--acc);color:var(--acc)}
main{max-width:1120px;margin:0 auto;padding:8px 20px 60px}
section.lesson,section.plain{padding-top:32px;border-top:1px solid var(--line);margin-top:28px}
section.lesson>*:not(figure):not(.tw):not(pre):not(details):not(.box),section.plain>*:not(figure):not(.tw):not(pre):not(details):not(.box){max-width:800px}
h2{font-size:1.65rem;margin:.2rem 0 .6rem;display:flex;align-items:center;gap:12px}
h2 .num{display:inline-flex;align-items:center;justify-content:center;width:2.1rem;height:2.1rem;border-radius:50%;background:var(--acc);color:var(--bg);font-size:1.1rem}
h3{font-size:1.15rem;margin:2rem 0 .4rem;color:var(--acc)}
.goal{background:var(--info);border-left:4px solid var(--infob);padding:10px 14px;border-radius:6px}
main a{color:var(--acc)}
code{background:var(--code);padding:.08em .35em;border-radius:4px;font:0.92em ui-monospace,SFMono-Regular,Menlo,monospace}
pre{background:var(--code);padding:12px 14px;border-radius:8px;overflow:auto;margin:.8rem 0;max-width:100%}
pre code{background:none;padding:0;font-size:.88rem;line-height:1.55}
pre.eq{border-left:4px solid var(--acc);background:var(--card);border-top:1px solid var(--line);border-right:1px solid var(--line);border-bottom:1px solid var(--line)}
figure{margin:1.4rem 0}figure img{width:100%;height:auto;background:#fff;border:1px solid var(--line);border-radius:8px;display:block}
figcaption{font-size:.88rem;color:var(--mut);margin-top:.4rem}
.tw{overflow-x:auto;margin:.9rem 0}table{border-collapse:collapse;width:100%;font-size:.92rem;background:var(--card)}
th,td{border:1px solid var(--line);padding:6px 10px;text-align:left;vertical-align:top}th{background:var(--code);font-weight:600}
.box{margin:1.1rem 0;padding:10px 16px;border-radius:8px;border-left:4px solid;max-width:800px}
.box strong{display:block;margin-bottom:.2rem}.box p,.box ul{margin:.3rem 0}.box ul{padding-left:1.2rem}
.box.ok{background:var(--ok);border-color:var(--okb)}.box.warn{background:var(--warn);border-color:var(--warnb)}.box.info{background:var(--info);border-color:var(--infob)}.box.no{background:var(--no);border-color:var(--nob)}
details{margin:.8rem 0;border:1px solid var(--line);border-radius:8px;padding:2px 14px;background:var(--card);max-width:800px}
details>summary{cursor:pointer;font-weight:600;padding:8px 0;color:var(--acc)}
.st{display:inline-block;padding:1px 9px;border-radius:999px;font-size:.8rem;font-weight:600;white-space:nowrap}
.st.ok{background:var(--ok);color:var(--okb)}.st.part{background:var(--warn);color:var(--warnb)}.st.no{background:var(--no);color:var(--nob)}
p.run{color:var(--mut);border-top:1px dashed var(--line);padding-top:8px}
footer{max-width:1120px;margin:0 auto;padding:20px;color:var(--mut);font-size:.85rem;border-top:1px solid var(--line)}
@media print{nav.toc{display:none}figure,table{break-inside:avoid}}
"""


def intro(passed, failed, ng):
    S = lessons.STATUS
    rows = [
        ["1", "평면형 NMOS 하나의 I-V", "Level 1", "손 계산 = 코드 = <code>.op</code>", S["ok"]],
        ["2", "저항 부하: Newton 반복", "Level 1", "손 계산 5회 반복 = 솔버", S["ok"]],
        ["3", "커패시터: transient", "Level 1", "손 계산 한 스텝 = 솔버, RC 이론값", S["ok"]],
        ["4", "CMOS 인버터", "Level 1", "Vm·이득·에너지: 공식 = 솔버", S["ok"]],
        ["5", "EKV: subthreshold", "EKV", "swing·Vds 의존성: 이론 = 솔버", S["ok"]],
        ["6", "채널 전하 모델", "EKV + 전하", "교과서 값(½, ⅔, 0.4)·전하 보존. 외부 시뮬레이터와는 비교하지 않음", S["part"]],
        ["7", "ngspice 교차검증", "Level 1", f"ngspice {ng}와 같은 netlist 비교", S["ok"]],
        ["8", "Verilog-A / OSDI", "EKV (VA)", "<b>실행하지 못함</b>. 절차와 소스만 수록", S["no"]]]
    s = f"""
<section id="intro" class="plain"><h2><span class="num">0</span>시작하기</h2>
<p>이 교재는 <b>SPICE를 처음 접하는 사람</b>이 평면형(planar) MOSFET의 compact model을 직접 계산해 보면서 SPICE가 회로를 푸는 방식을 이해하도록 만들었습니다. 직접 만든 작은 SPICE(<code>minispice</code>, Python)를 쓰고, 마지막에는 실제 시뮬레이터(ngspice)와 비교합니다.</p>
<p>모든 레슨은 같은 순서입니다: <b>회로도 → 손 계산 → 코드·시뮬레이션 → 그래프 → 요약</b>. 본문의 숫자는 이 페이지를 만들 때 코드를 실제로 실행해서 넣은 값입니다.</p>
<h3>전체 지도와 검증 상태</h3>
{lessons.tbl(["레슨", "주제", "모델", "무엇과 비교했나", "상태"], rows)}
<p>자동 테스트: <b>{passed}개 통과{f", {failed}개 실패" if failed else ""}</b> (<code>pytest</code>, 모델 도함수·전하 모델·회로 해석).</p>
<h3>표기 약속</h3>
<ul>
<li><code>Vxy</code> = x 단자 전압 − y 단자 전압 (예: <code>Vgs = Vg − Vs</code>). 아래 첨자 <code>s</code>는 source입니다.</li>
<li>netlist에서 <code>V…</code>로 시작하는 이름은 전압원, <code>R…</code> 저항, <code>C…</code> 커패시터, <code>M…</code> MOSFET입니다. 이름의 나머지 글자는 아무 이름이어도 됩니다.</li>
<li>SPICE의 전압원 전류는 <b>+ 단자로 들어가는 방향이 양수</b>입니다. 전원이 회로에 전류를 공급하면 음수로 나옵니다.</li>
<li>단위 접두사: f = 10⁻¹⁵, p = 10⁻¹², n = 10⁻⁹, µ = 10⁻⁶, m = 10⁻³ (netlist에서는 <code>u</code>).</li></ul>
<h3>준비</h3>
{lessons.code('''git clone https://github.com/soodaddy/spice && cd spice
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
brew install ngspice                    # 레슨 7 (macOS)
.venv/bin/python -m pytest -q           # 테스트
cd examples && ../.venv/bin/python lesson1_single_mosfet.py   # 레슨별 스크립트
.venv/bin/python textbook/build.py      # 이 교재를 다시 생성 (docs/index.html)''')}
</section>"""
    return s


def appendix(passed, failed):
    return f"""
<section id="appendix" class="plain"><h2><span class="num">★</span>부록</h2>
<h3>A. 알려진 한계 모음</h3>
<ul>
<li><b>Level 1</b>: 문턱 아래 전류 없음, 이동도 저하·속도 포화·단채널 효과 없음. λ는 L에 따라 변하지 않는 고정값.</li>
<li><b>EKV</b>: 장채널 단순형. 몸체 효과의 전압 의존성, 이동도 저하, 속도 포화, DIBL 없음.</li>
<li><b>전하 모델</b>: 공핍·축적(벌크) 전하 없음, 용량 행렬은 수치 미분. n &gt; 1에서 Cgb &lt; 0.</li>
<li><b>솔버</b>: 조밀(dense) 행렬이라 수백 노드까지. gmin = 10⁻¹² S 고정. 초기조건(.ic, UIC) 미지원이라 링 오실레이터는 전류 펄스로 기동. 수렴 보조는 전압 스텝 제한, gmin/source stepping, 시간 스텝 분할만 있음.</li>
<li><b>ngspice 비교</b>는 Level 1만. EKV·전하 모델의 외부 대조는 아직 없음(레슨 8).</li></ul>
<h3>B. 개발 중 발견하고 고친 문제</h3>
<ol>
<li><b>펄스 에지와 trapezoidal</b>: 에지가 시간 스텝 중간에 있으면 첫 스텝 결과가 정확히 절반이 되었습니다 → 소스 꺾임점에 시간 점을 맞추도록 수정(레슨 3).</li>
<li><b>레슨 2의 반복 로그 설명</b>: 예상으로 쓴 설명이 실제 솔버 로그와 달랐습니다 → 로그를 훅(<code>trace</code>)으로 직접 찍어 설명을 다시 썼습니다.</li>
<li><b>EKV 비교 조건</b>: Vds = 1.0 V에서 비교하니 포화가 아니라서 EKV/Level 1 비율이 1/n과 어긋났습니다 → 모든 비교를 Vds = 1.8 V(포화)로 통일(레슨 5).</li>
<li><b>전하 모델의 단자 순서 오류와 무의미한 테스트</b>: 링이 오히려 빨라지는 결과로 발견했고, 용량 테스트가 허용오차 때문에 항상 통과하고 있었습니다 → 수정하고 테스트를 무차원으로 다시 작성(레슨 6).</li></ol>
<h3>C. 코드 지도</h3>
{lessons.tbl(["경로", "내용"], [
    ["<code>minispice/models.py</code>", "Level1, EKV(전류 + 전하). 공통 인터페이스 <code>evaluate()</code>, <code>charges()</code>"],
    ["<code>minispice/circuit.py</code>", "R, C, V, I, MOSFET 요소와 각자의 MNA stamp"],
    ["<code>minispice/analysis.py</code>", "Newton, gmin/source stepping, <code>.op</code> <code>.dc</code> <code>.tran</code>"],
    ["<code>minispice/netlist.py</code>", "SPICE 문법 파서 (R C V I M, .model .op .dc .tran, PULSE)"],
    ["<code>examples/lessonN_*.py</code>", "레슨별 스크립트(수치 출력 + 그림)"],
    ["<code>examples/va/ekv_simple.va</code>", "레슨 8의 Verilog-A (미컴파일)"],
    ["<code>tests/</code>", f"테스트 {passed}개"],
    ["<code>textbook/</code>", "이 교재의 생성 코드 (<code>build.py</code>)"]])}
</section>"""


def main():
    if "--no-run" not in sys.argv:
        run_all()
    passed, failed = run_tests()
    ng = lessons.J(7)["ngspice_version"]
    nav = [("intro", "시작하기")] + [(f"l{n}", f"{n}. {t}") for n, t in
           ((1, "NMOS 하나"), (2, "Newton"), (3, "Transient"), (4, "CMOS 인버터"), (5, "EKV"), (6, "전하 모델"), (7, "ngspice"), (8, "OSDI"))] + [("resources", "추천 자료"), ("appendix", "부록")]
    toc = "".join(f'<li><a href="#{a}">{t}</a></li>' for a, t in nav)
    body = intro(passed, failed, ng) + "".join(f() for f in (lessons.lesson1, lessons.lesson2, lessons.lesson3, lessons.lesson4,
                                                             lessons.lesson5, lessons.lesson6, lessons.lesson7, lessons.lesson8)) + lessons.resources() + appendix(passed, failed)
    today = datetime.date.today().isoformat()
    page = f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SPICE로 배우는 MOSFET Compact Model</title>
<meta name="description" content="평면형 MOSFET compact model을 직접 계산하며 SPICE가 회로를 푸는 방식을 배우는 8개 레슨">
<style>{CSS}</style></head><body>
<header class="hero"><h1>SPICE로 배우는 MOSFET Compact Model</h1>
<p>평면형(planar) MOSFET을 한 개부터 풀어 보며 SPICE가 방정식을 푸는 방식, 모델의 의미, 그리고 실제 시뮬레이터와의 비교까지. 총 8개 레슨.</p>
<p>생성: {today} · Python minispice · ngspice {ng}</p></header>
<nav class="toc"><ul>{toc}</ul></nav>
<main>{body}</main>
<footer>이 페이지는 <code>python textbook/build.py</code>로 생성됩니다. 본문의 수치는 생성 시점의 코드 실행 결과이며, 그림은 <code>examples/</code>의 스크립트가 만듭니다.</footer>
</body></html>"""
    out = ROOT / "docs" / "index.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(page, encoding="utf-8")
    print(f"wrote {out}  ({out.stat().st_size/1e6:.2f} MB), tests: {passed} passed, {failed} failed")


if __name__ == "__main__":
    main()
