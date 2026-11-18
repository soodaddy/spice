# spice
spice study

SPICE가 MOSFET compact model을 푸는 방식을 **직접 만들어 보며** 배우는 학습 프로젝트입니다.
평면형(planar) MOSFET 한 개부터 시작해서 CMOS 인버터, EKV 모델, 채널 전하 모델, ngspice 교차검증, FinFET과 GAA(나노시트), 그리고 DRAM 셀(워드라인·비트라인·저장 커패시터)과 비트라인을 공유하는 여러 셀까지 12개 레슨으로 구성했습니다.

## 교재

**[`docs/index.html`](docs/index.html)** — 12개 레슨 교재 (그림과 슬라이더로 조작하는 3D·회로도 시각화가 포함된 단일 HTML 파일). 저장소를 받은 뒤 브라우저로 열면 됩니다.
(GitHub Pages로 공개하려면 저장소 Settings → Pages에서 `main` 브랜치의 `/docs` 폴더를 지정하면 됩니다. 현재는 설정하지 않았습니다.)

| 레슨 | 내용 | 상태 |
|---|---|---|
| 1 | 평면형 NMOS 하나의 I-V (Level 1) | 실행·검증됨 |
| 2 | 저항 부하: Newton 반복으로 동작점 구하기 | 실행·검증됨 |
| 3 | 커패시터: 시간 스텝으로 풀기 (transient) | 실행·검증됨 |
| 4 | CMOS 인버터 | 실행·검증됨 |
| 5 | EKV 모델: subthreshold 전류 | 실행·검증됨 |
| 6 | 채널 전하 모델 (MOSFET 내부 용량) | 부분 검증 (외부 시뮬레이터와는 비교하지 않음) |
| 7 | ngspice 교차검증 (Level 1) | 실행·검증됨 |
| 8 | Verilog-A / OSDI | **미실행**: 절차와 소스만 수록, `examples/va/ekv_simple.va`는 컴파일해 보지 않음 |
| 9 | FinFET | 부분 검증: 구조·기하는 계산, 설계 경험칙은 강의자료. **n, η, fin 폭은 가상의 예시값** |
| 10 | GAA / 나노시트 | 부분 검증: 기하 유도와 방향성 계산. **나노시트 치수, n, η는 가상의 예시값** |
| 11 | DRAM 1T1C 셀 | 부분 검증: 쓰기·읽기(전하 공유, 센스앰프)는 손 계산 = minispice = ngspice(Level 1). **유지 시간은 외부 비교 없는 누설 ODE, Cs·Cbl·누설 값은 가상의 예시값** |
| 12 | 비트라인을 공유하는 셀 2개·4개 | 부분 검증: 전하 공유 일반식·쓰기→읽기 순서는 minispice = ngspice(Level 1). **이웃 접근에 의한 유지 시간은 가정(활동도)에 따른 ODE, 큰 N은 손 계산, 값은 가상의 예시값** |

## 구성

```
minispice/    작은 SPICE (Python): Level1·EKV 모델, MNA, Newton, .op/.dc/.tran, netlist 파서
examples/     레슨별 스크립트(lessonN_*.py), 예제 netlist(*.cir), Verilog-A(va/)
tests/        pytest (모델 도함수, 전하 모델, 회로 해석)
textbook/     교재 생성 코드 (build.py)
docs/         생성된 교재 (index.html)
```

## 시작하기

```bash
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/python -m pytest -q                      # 테스트
cd examples && ../.venv/bin/python lesson1_single_mosfet.py   # 레슨 스크립트 (수치 출력 + 그림)
brew install ngspice                               # 레슨 7에만 필요 (macOS)
.venv/bin/python textbook/build.py                 # 교재(docs/index.html) 다시 생성
```

교재의 숫자는 `build.py`가 레슨 스크립트와 테스트를 실제로 실행해서 넣습니다.
레슨 8을 뺀 모든 레슨에는 슬라이더로 입력을 바꾸면 3D 구조와 회로도의 전압·전류가 바뀌는 시각화가 있습니다 (`textbook/js/`, 외부 라이브러리 없음). JavaScript 모델은 `tests/test_js_parity.py`가 Python 모델과 대조합니다 (node 필요).
`examples/out/`(그림, JSON)은 생성물이라 저장소에 포함하지 않았습니다.

## 라이선스

MIT (`LICENSE`)
