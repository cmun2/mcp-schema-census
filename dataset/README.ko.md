# mcp-schema-census (한국어 요약)

> 1차 문서는 영어다. 전체 내용은 [README.md](README.md) · [METHODOLOGY.md](METHODOLOGY.md)
> · [CONSTRAINTS.md](CONSTRAINTS.md) · [LIMITATIONS.md](LIMITATIONS.md) · [LICENSE](LICENSE)를
>보라. 이 문서는 그 요약이며, 숫자가 어긋나면 영어 문서가 기준이다.

**공개 MCP 서버 617개를 실제로 stdio로 기동해 받은 `tools/list` 스키마 14,804개에,
세 provider의 strict 판정축을 얹은 결과.**

스키마 수집 **2026-08-09** / provider 제약 문서 확인 **2026-08-23** / 판정 **2026-08-23**.

---

## 숫자를 인용하기 전에

**63.0%는 "MCP 서버의 63%가 죽어 있다"는 뜻이 아니다.** opt-in 숫자다.
클라이언트가 서버의 `inputSchema`를 그대로 가져다 Anthropic Messages API에
`strict: true`로 넘길 때, 617개 중 63.0%가 문서가 거부한다고 명시한 값을
적어도 하나 가지고 있다는 뜻이다.

opt-in이 **아닌** 축, 즉 클라이언트가 아무것도 켜지 않아도 적용되는 축은 **0.0%**다.

| 축 | opt-in? | 실패 서버 |
|---|---|---:|
| **A** MCP 사양 적합 (`client.listTools()`가 throw → 그 서버 도구 전체 소실) | **아니오** | **0/617 = 0.0%** |
| **C0** Anthropic Messages API 기본선 (루트 `oneOf`/`allOf`/`anyOf`) | **아니오** | **0/617 = 0.0%** |

이 0.0%는 새 결과가 아니고 철회된 것도 아니다. 2026-08-09 측정의 결론이 그것이었고,
세 번째 provider 축을 얹어도 움직이지 않았다. **비-opt-in 축에서 이 생태계는 깨끗하다.**
흥미로운 결과는 실패율 자체가 아니라, **하나의 코퍼스 위에서 세 축의 판정이 44.9%p
어긋난다**는 사실이다.

**여기서 "opt-in"이 정확히 무슨 뜻인지 — 과잉 해석하기 쉬운 지점이라 적는다.**
C축 제약 목록이 적용되려면 *클라이언트*가 그 도구에 `strict: true`를 붙여야 한다는
뜻이다. **서버 작성자가 정하는 게 아니다.** 작성자가 통제하는 건 스키마지 플래그가
아니고, 남의 클라이언트가 그걸 켜는 것을 막을 수 없다. 그러니 "opt-in"은
"안전하다"의 동의어가 아니라 "우리가 관측할 수 있는 클라이언트에서는 아직 발동하지
않았다"는 뜻이다. 63.0%는 진행 중인 장애가 아니라 **노출 면적**으로 읽어야 한다.

그리고 opt-in이 *아닌* 축에서는 사용자 쪽 탈출구도 없다.
[Countly/countly-mcp-server#64](https://github.com/Countly/countly-mcp-server/issues/64)는
Claude Code의 `skipSchemaValidation` 옵션이 "로컬 검증만 우회할 뿐 API 자체는 여전히
스키마를 거부한다"고 보고한다. 위 표의 C0 행이 **아니오**인 이유가 그것이다.
근거가 된 공개 이슈 7건은 [현장 근거](#현장-근거--실제로-400을-맞고-올라온-공개-이슈-7건)에 있다.

**API는 호출하지 않았다.** 판정 근거는 ① provider 공개 제약표(URL·축어 인용),
② provider 자신의 프로덕션 코드(MCP TS SDK 파서, `openai-agents`의
`ensure_strict_json_schema`, Anthropic Python SDK의 `transform_schema`),
③ 공개 보고된 관측 400들이다 — 그중 7건을 직접 열어 읽고 축에 매핑한 결과가
[현장 근거](#현장-근거--실제로-400을-맞고-올라온-공개-이슈-7건)에 있다. **실 엔드포인트 대상 end-to-end 검증은 하지 않았다**
(NO-SPEND 제약). 문서가 침묵하는 지점은 추측하지 않고 모호로 분류했다.

### 문서 전체에서 지키는 표현 규칙

"이 서버는 깨졌다"라고 쓰지 않는다. **"이 스키마는 이 축에서 이 포인터의 이 값 때문에
거부된다"**라고 쓴다. `minimum: 1`은 결함이 아니라 올바른 JSON Schema이고, 다만
한 provider의 opt-in 서브셋이 그것을 받지 않을 뿐이다. 이 레포에는 서버 순위표도,
"최악의 서버" 표도 없다. 재사용할 때도 그렇게 유지해 주기를 부탁한다.

---

## 판정이 틀렸다고 생각하면

**이슈를 열어 달라.** 판정은 "공개된 문장이 특정 값을 거부한다"는 주장이고,
문장과 값 둘 다 검증 가능하며 provider 문서는 바뀐다.

`violations.jsonl`의 모든 행에는 그 판정 하나만 즉시 재현하는 `repro` 명령이 들어 있다.

```bash
jq -r 'select(.code=="C2-numeric-constraint:minimum") | .repro' violations.jsonl | head -1
# python3 scripts/explain.py --server "io.github.1clawAI/1claw-mcp" \
#   --code "C2-numeric-constraint:minimum" --tool "test_binding" --pointer "#/properties/timeout_ms"
```

`explain.py`는 `violations.jsonl`을 믿지 않는다. 스키마를 직접 읽어 규칙을 다시 돌리고,
기록된 행과 일치하는지(`MATCH` / `MISMATCH`)까지 출력한다. 그 출력을 이슈에 붙이면 된다.

**서버 작성자:** 자기 서버의 행을 빼고 싶으면 이슈에 그렇게 적어 달라. 뺀다.
법적 논증을 먼저 할 필요 없다.

---

## 3축 요약

패키지 기준 전역 dedup. **N = 617 서버 / 14,804 도구.**

| 축 | 무엇을 재는가 | 판정자 | opt-in? | 서버 | 도구 |
|---|---|---|---|---:|---:|
| **A** | MCP 사양 — `listTools()`가 throw해 서버 도구 전체가 사라짐 | MCP TS SDK 1.30.0 `ListToolsResultSchema.safeParse` (실제 프로덕션 파서) | 아니오 | **0/617 = 0.0%** | 0.0% |
| **B** | OpenAI `strict` 하드 거부 | `openai-agents` `ensure_strict_json_schema` (실제 변환기) | 예 | **170/617 = 27.6%** | 5.9% |
| **B′** | OpenAI `strict` 조용한 제약 상실 | 문서화된 미지원 키워드표 | 예 | 351/617 = 56.9% | 22.5% |
| **C0** | Anthropic API 기본선 (루트 조합자) | 관측 400 (claude-code#10606), **문서에는 없음** | 아니오 | **0/617 = 0.0%** | 0.0% |
| **C** | Anthropic `strict: true` 서브셋 | 공개 제약표 축어 인용 + 공식 Python SDK 1.0.0 `transform_schema` 교차검증 | 예 | **389/617 = 63.0%** | **23.0%** |
| **CL** | Anthropic 요청 복잡도 상한 (strict 도구 20 / 선택 파라미터 24 / union 16) | 공개 explicit limits 표 | 예 | **230/617 = 37.3%** | 해당 없음 |
| **C\*** | Anthropic 어느 하나라도 | | | **447/617 = 72.4%** | 23.0% |

모집단별 (holdout은 A·B 규칙 확정 **후** 수집한 분리 슬라이스):

| 슬라이스 | N | A | B | C0 | C | CL | C\* |
|---|---:|---:|---:|---:|---:|---:|---:|
| npm | 298 | 0.0% | 26.2% | 0.0% | 62.8% | 38.6% | 73.5% |
| pypi | 117 | 0.0% | 42.7% | 0.0% | 53.8% | 41.9% | 63.2% |
| holdout | 202 | 0.0% | 20.8% | 0.0% | **68.8%** | 32.7% | 76.2% |

holdout이 튜닝 슬라이스보다 오히려 높다. C는 규칙을 쓴 슬라이스의 산물이 아니다.

---

## 세 축은 같은 것을 재지 않는다

이게 이 데이터셋의 새 정보다.

```
                   C* 실패   C* 통과
    B 실패            170        0
    B 통과            277      170
```

- **포함 사슬 A ⊂ B ⊂ C\***. 공개 데이터에서 검증됨(`stats.py`가 `True / True` 출력). 0 ⊂ 170 ⊂ 447.
- **Jaccard(B, C\*) = 0.380**
- **P(C\* | B) = 1.000** — OpenAI strict에서 깨지는 서버는 예외 없이 Anthropic에서도 깨진다
- **P(B | C\*) = 0.380** — 역은 성립하지 않는다
- **기존 두 축(A·B)에서 깨끗한데 Anthropic 축에서 깨지는 서버: 277/617 = 44.9%**
- **OpenAI에서는 "조용한 상실"에 그쳤는데 Anthropic에서는 하드 거부: 219/617 = 35.5%**

원인은 같은 키워드를 두 provider가 다르게 처분하기 때문이다.

| 키워드 | OpenAI `strict` | Anthropic `strict: true` |
|---|---|---|
| `additionalProperties` ≠ `false` | 거부 | 거부 |
| `minimum` / `maximum` | **조용히 제거** | **거부** |
| `minLength` / `maxLength` | **조용히 제거** | **거부** |
| `maxItems` / `uniqueItems` | **조용히 제거** | **거부** |
| `minItems` ≥ 2 | 조용히 제거 | 거부 |
| `pattern` (정규식) | 조용히 제거 | **지원** |
| 선택 파라미터 | 전 속성 `required` 강제 | 지원 (요청당 24개 상한) |
| strict 도구 > 20 | 그런 상한 없음 | 거부 |

B축은 단일 원인(`additionalProperties`, 도구 히트의 99.9%)이 지배한다.
C축을 지배하는 것은 `minimum`/`maximum`/`minLength`/`maxLength` — **B축이 조용히 버리던
바로 그 키워드들**이다. 두 축이 거의 겹치지 않는 이유가 이것이다.

---

## 선행연구

여기 인용한 것은 전부 **2026-08-23에 실제로 열어서 읽었다.** 열지 못한 것은
요약하지 않고 "열지 못했다"라고 적었다.

### 논문

| 연구 | 코퍼스 | 무엇을 쟀는가 | 열어봤나 |
|---|---:|---|---|
| Li & Gao, *A First Look at the Security Issues in the Model Context Protocol Ecosystem*, DSN 2026 — [arXiv:2510.16558](https://arxiv.org/html/2510.16558) | 레지스트리 6곳, 서버 **67,057** | 레지스트리의 검수·소유권 확인 취약과, 통합 이후 공격자가 통제하는 도구 **메타데이터**로 인한 공격(tool poisoning, tool shadowing, context-dangling tool). 자체 도구 `MCPInspect`로 취약 서버 833개, 의심스러운 description 18개 검출. | 예 |
| Lin, Ruan, Liu & Zhao, *MCPCorpus* — [arXiv:2506.23474](https://arxiv.org/abs/2506.23474) (2025-06-30) | 서버 약 **14,000** + 클라이언트 **300** | 재현 가능한 생태계 스냅샷. 각 항목을 신원·인터페이스 설정·GitHub 활동·메타데이터를 포괄하는 20종 이상 속성으로 정규화. 적합성 측정이 아니라 코퍼스 구축. | 예 |
| Chen et al. (푸단대 / Shanghai Innovation Institute), *Rethinking MCP Security: A Large-Scale Study of Runtime MCP Servers and Security Scanner Reliability* — [arXiv:2607.11086](https://arxiv.org/html/2607.11086) (2026-07-13) | 10개 마켓에서 고유 서버 **64,611**, 그중 실제로 기동해 런타임 상호작용까지 간 것 **37,288** (배포 성공률 57.7%) | MCP 보안 스캐너의 신뢰성. 상호작용 가능한 서버의 **96.89%**가 8개 스캐너 중 최소 하나에서 위험으로 표시됨. 스캐너 평균 정밀도 45.53%(10.40–96.88%), 스캐너 간 평균 Jaccard 15.66%, 확인된 취약점에 대한 재현율 24.17%. | 예 |
| Hasan, Li, Fallahzadeh, Rajbahadur, Adams & Hassan, *MCP at First Glance: Studying the Security and Maintainability of MCP Servers* — [arXiv:2506.13538](https://arxiv.org/abs/2506.13538) (v1 2025-06-16, v5 2026-04-13) | 오픈소스 서버 **1,899** | 소스코드 건강성. 범용 정적분석 + MCP 전용 스캐너. 일반 취약점 7.2%, MCP 고유 tool poisoning 5.5%, 코드 스멜 66%, 기존 연구와 겹치는 버그 패턴 14.4%. | 예 |

**네 편 모두 wire 스키마 적합성을 재지 않고, provider의 strict 모드 제약 집합을
적용하지 않는다.** 셋은 서버(또는 서버를 판정하는 스캐너)의 보안 속성을, 하나는
메타데이터 코퍼스를 다룬다.

### 우리 위치

**코퍼스 규모에서 우리는 넷 모두에 크게 밀린다 — 617 대 67,057.** 이 격차는
실재하고, 말로 지우지 않는다. 우리 서버는 stdio로 실제 기동해 살아 있는
`tools/list` 응답을 받은 것이라 레지스트리 크롤보다는 위 런타임 연구의 방법에
가깝지만, 규모는 비교 대상이 아니다.

우리가 주장하는 것은 규모가 아니다. **여러 provider의 strict 모드 제약 집합을
하나의 동일한 코퍼스에 교차 적용해, 축들이 서로 얼마나 어긋나는지를 측정한 것**이다
— 같은 스키마 위에서 OpenAI strict 변환기가 거부하는 것과 Anthropic strict
서브셋이 거부하는 것 사이의 44.9%p 격차. 이건 서버 품질에 대한 질문이 아니라
provider 간 불일치에 대한 질문이고, 단일 축 측정에서는 나올 수 없다.

**우리 검색 범위 안에서는 같은 각도의 선행연구를 찾지 못했다.** 전수조사를 하지
않았고, "못 찾았다"는 우리 검색에 대한 진술이지 문헌에 대한 진술이 아니다. 이런
연구가 있다면 인용을 받고 싶다.

### 서버 작성자가 지금 쓸 수 있는 도구

더 직접적인 의미의 선행 작업이다. 자기 스키마가 받아들여지는지 알고 싶은 서버
작성자에게는 이미 이런 선택지가 있다. 각각 2026-08-23에 직접 확인했고, 확인한
질문은 하나다 — **provider의 strict 모드 제약을 보는가, MCP 사양만 보는가?**

| 도구 | 무엇을 검사하나 | 우리 축으로는 | 어떻게 확인했나 |
|---|---|---|---|
| **공식 MCP Inspector** — `npx @modelcontextprotocol/inspector --cli --method tools/list` | 서버에 붙어 `tools/list`·`resources/list`·`prompts/list`·`tools/call` 결과를 출력. 스키마 엄격성 검증 없음. | 없음 — 검증기가 아니라 클라이언트 | `clients/cli/src/cli.ts`(40,381바이트)를 읽음: **문자열 `strict` 출현 0회**, 거기 정의된 롱폼 플래그 목록에 `--strict` 없음 |
| **`@yawlabs/mcp-compliance`** — `npx @yawlabs/mcp-compliance@latest test <대상>` | MCP 사양 2025-11-25 기준 8개 범주(transport·lifecycle·tools·resources·prompts·error handling·schema validation·security) 88개 테스트, A–F 등급. 여기 있는 `--strict`는 CI용 **종료 코드** 모드지 스키마 엄격성이 아니다. | **A** (MCP 사양). `tools-schema` 규칙이 문자 그대로 "All tools have name and inputSchema" — 우리 `A1`/`A5`. | 공개된 규칙 카탈로그 `mcp-compliance-rules.json`(47,917바이트, 규칙 88개)을 읽음: `anyOf`·`oneOf`·`allOf`·`additionalProperties`·`minLength`·`maxLength`·`minimum`·`maximum`·`maxItems`·`uniqueItems`·`input_schema`·`Anthropic`·`OpenAI` **전부 0회** |
| **mcptools.tools** — [MCP Schema Validator](https://mcptools.tools/schema-validator) | 브라우저 내 실행. 자체 설명: "MCP 사양 스키마"에 대해 검증 — 도구 이름 문자 집합, `inputSchema`가 `type: "object"`인 JSON Schema 객체인지, manifest·client config 구조. | **A**, 그리고 우리가 안 재는 client-config 위생 | 페이지를 받아 확인: 인라인 JS 포함 소스에 provider 제약 키워드 0회 |
| **DevTk.AI** — [MCP Config Validator](https://devtk.ai/en/tools/mcp-validator/) | 서버 config를 MCP 사양 기준으로 검증 + 스타일 경고(description 20자 미만, `required` 배열 누락, 이름 중복). | **A**, 그리고 스타일 조언 | 페이지를 받아 확인: 인라인 JS 포함 소스에 provider 제약 키워드 0회 |
| **mcpserverspot** — [validator](https://www.mcpserverspot.com/tools/validator) | **열지 못했다.** | 불명 | 2026-08-23 기준 해당 URL이 브라우저 에이전트 fetch와 `curl` 양쪽에 `HTTP 402 DEPLOYMENT_DISABLED` 반환. 검색 인덱스 스냅샷상 "compatibility warnings"는 *도구 50개 초과*와 *version 문자열 누락* — 클라이언트 성능·위생이지 provider 제약이 아님 — **이건 2차 정보이고 직접 확인하지 못했다.** |
| **mcp-probe / `mcp-conform`** — [castrocrest/mcp-probe-cli](https://github.com/castrocrest/mcp-probe-cli) (#1005 스레드에서 발견) | JSON-RPC 봉투, initialize 응답, `tools/list` 구조, JSON Schema 유효성(Claude Code가 거부하는 bare `true` 스키마 검출), 에러 코드, method-not-found. | **A** — bare `true` 케이스가 우리 `A2` | README를 읽음 |

**돌아다니는 정보 하나를 바로잡는다.**
`npx @modelcontextprotocol/inspector --cli --method tools/list --strict`는 동작하지
않는다. **Inspector에는 `--strict` 플래그가 없다.** 그 문자열은
[modelcontextprotocol/inspector#1005](https://github.com/modelcontextprotocol/inspector/issues/1005)의
*제안 본문*에서 나온 것이고, 그 이슈는 **열려 있으며 작업 승인도 나지 않았다** —
2026-08-01에 7/16("Medium")로 트리아지, 프로젝트 보드 상태 "Incoming". 게다가
#1005가 제안하는 것도 우리 기준으로는 **A축**이다: bare `true` 스키마,
`"type": ["null","boolean"]`, `type` 누락. 그 이슈의 첫 예시부터 Go SDK가
`interface{}`에 대해 `true`를 뱉는 케이스다.

**결론을 그대로 적는다.** 위 도구들이 검사하는 것은 전부 이 코퍼스가 **이미
0.0%인 축**(MCP 사양 적합, 0/617)이거나, 우리가 아예 재지 않는 client-config
축이다. OpenAI `strict`·Anthropic `strict: true`·Anthropic Messages API 기본선을
적용하는 것은 하나도 없다. 이건 그 도구들의 **커버리지**에 대한 진술이지 품질에
대한 진술이 아니다. 특히 `mcp-compliance`는 우리보다 훨씬 넓게 프로토콜을
검사하고, 루브릭과 규칙 카탈로그를 CC BY로 공개해 규칙을 포크할 수 있게 해 뒀다.

---

## 현장 근거 — 실제로 400을 맞고 올라온 공개 이슈 7건

이 데이터셋은 API를 호출하지 않았으므로 여기 있는 모든 400은 **예측**이다. 그
한계는 그대로 유지하고 덜어내지 않는다. 아래는 그 자리에 놓을 수 있는 가장 가까운
대체물이다 — **실제로 400을 받은 사람들이 올린 공개 이슈**. 전부 2026-08-23에
직접 열어 읽고, 축과 판정 코드에 매핑하거나 **매핑하지 않았음을 명시**했다.

매핑 규칙: 에러 문자열이 우리 코드가 다루는 구성요소를 실제로 지목할 때만
매핑한다. 그렇지 않으면 가장 가까운 축으로 억지로 밀지 않고 **대응 불명**으로 둔다.

| # | 보고 | 날짜 / 클라이언트 | 에러 (축어) | 축 | 코드 |
|---|---|---|---|---|---|
| 1 | [anthropics/claude-code#10606](https://github.com/anthropics/claude-code/issues/10606) — 스테일봇이 `not_planned`로 닫음, 메인테이너 응답 없음 | 2025-10-30, Claude Code v2.0.21–2.0.29 | `tools.XX.custom.input_schema: input_schema does not support oneOf, allOf, or anyOf at the top level` | **C0** | `C0-root-combinator:*` |
| 2 | [ProfSynapse/claudesidian-mcp#6](https://github.com/ProfSynapse/claudesidian-mcp/issues/6) | 2025-06-27, Claude Code **v1.0.35** | 동일 문자열, `tools.136` | **C0** | `C0-root-combinator:*` |
| 3 | [Countly/countly-mcp-server#64](https://github.com/Countly/countly-mcp-server/issues/64) — 업스트림에서 수정됨 | 2026-02-23, Claude Code | 동일 문자열, `tools.29`. 보고자는 최상위 `anyOf`의 원인을 손으로 쓴 스키마가 아니라 `@modelcontextprotocol/sdk` ≥1.26.0의 Zod→JSON Schema 변환으로 지목 | **C0** | `C0-root-combinator:*` |
| 4 | [microsoft/pylance-release#7986](https://github.com/microsoft/pylance-release/issues/7986) | 2026-04-13, VS Code Copilot + Claude Sonnet 4.6 | `tools.47.custom.input_schema.properties: Property keys should match pattern '^[a-zA-Z0-9_.-]{1,64}$'` — `$schema`가 *property 키*로 들어감 | **대응 불명** | — |
| 5 | [anthropics/claude-code#1690](https://github.com/anthropics/claude-code/issues/1690) — 메인테이너가 "IIUC, this is working as expected"로 닫음 | 2025-06-06, Claude Code v1.0.16, 로컬 WordPress MCP 서버 | `tools.16.custom.input_schema: JSON schema is invalid. It must match JSON Schema draft 2020-12` | **대응 불명** | — |
| 6 | [anthropics/claude-code#20720](https://github.com/anthropics/claude-code/issues/20720) — #11678의 중복으로 닫힘 | 2026-01-25, Claude Code v2.1.19 | 동일한 일반 draft-2020-12 메시지, `tools.17`. 보고자는 `{"mcpServers": {}}`, 즉 MCP 서버를 하나도 설정하지 않은 상태라고 명시 | **대응 불명** | — |
| 7 | [anthropics/claude-code#10858](https://github.com/anthropics/claude-code/issues/10858) — #8014의 중복으로 닫힘, v2.0.33부터 수정 보고 | 2025-11-02, `claude mcp serve`를 Claude Desktop이 읽음 | 400이 아님. tools/list 응답의 도구 6개에 `"strict": true`가 실려 Claude Desktop이 "No tools available"을 표시 — MCP 사양에 없는 Anthropic API 전용 필드 | **대응 불명** | — |

4–7을 매핑하지 않은 이유:

- **#4**는 실재하는 비-opt-in Messages API 제약(property 키 정규식)인데,
  **이 데이터셋은 그걸 아예 검사하지 않는다.** 보고 쪽 결함이 아니라 우리 규칙
  집합의 구멍이다. (참고용, 이 README의 어떤 카운트에도 들어가지 않음: 617개 중
  **2개** 서버가 그 정규식을 통과하지 못하는 property 키를 공개하고 있다 — 하나는
  `$schema`, 다른 하나는 MongoDB식 `$in`/`$ne`/`$eq`/`$nin`/`$and`. 재현:
  `jq -r 'select([.input_schema|..|objects|(.properties//{})|keys[]]|any(test("^[a-zA-Z0-9_.-]{1,64}$")|not))|.package' tools.jsonl | sort -u`.
  이 숫자는 **축이 아니고**, `STATS.txt`에 **없으며**, 어떤 판정도 움직이지
  않는다.) 그리고 이 스레드 자체가 미결이다 — Pylance 메인테이너는 재현하지
  못했고 VS Code가 `$schema` 키를 주입하는 것으로 의심한다.
- **#5**와 **#6**은 키워드를 하나도 지목하지 않는 일반 "draft 2020-12" 메시지이고,
  두 스레드 모두 스키마를 보여주지 않는다. 코드에 대응시킬 구성요소가 없다.
  #6은 MCP 서버를 하나도 설정하지 않았다고 보고하므로 애초에 이 코퍼스 밖이다.
- **#7**은 방향이 반대인 진짜 다른 종류의 실패다. API가 스키마를 거부한 게 아니라,
  **클라이언트가 사양에 없는 도구 레벨 필드를 거부**한 것이다. 우리 A축 오라클인
  공식 TypeScript SDK 파서는 `ToolSchema`가 `.catchall(z.unknown())`으로 끝나므로
  `strict` 같은 여분 키에 실패하지 않는다. 그래도 기록해 둔다 — provider API의
  어휘가 MCP wire 포맷 쪽으로 새어 나온 것이고, 이 데이터셋이 재는 바로 그 이음매를
  반대 방향에서 본 것이기 때문이다.

### #10606이 이 문서에서 바꾼 것과 바꾸지 않은 것

최상단 가드는 63.0%가 *opt-in* 숫자라고 말한다. #10606의 제목은 "Strict MCP schema
validation in v2.0.21+ breaks working MCPs with **no opt-out**"이고, 그게 사실이면
그 가드가 무너진다. 전문을 읽은 결과 무너지지 않는다 — 다만 다른 두 가지는 정말로
고쳐야 했고, 둘 다 프레이밍이지 산술이 아니다. **이 레포의 어떤 수치도 움직이지
않았다.**

1. **63.0%는 여전히 opt-in 숫자다.** #10606에 나오는 구체적 에러는 — 그리고 위 #2,
   #3도 — 전부 최상위 조합자 400이고, 그건 **C0축**이다. C0는 이미 여기서 opt-in이
   *아닌* 축으로 분류돼 있고 이미 **0/617 = 0.0%**로 보고돼 있다. 63.0%는 **C축**,
   즉 `strict: true` JSON Schema 서브셋(`minimum`, `maxLength`, `maxItems` …)이다.
   7건 중 어느 것도 클라이언트가 서버의 공개 스키마에 `strict: true`를 붙이는
   장면을 보여주지 않는다. 이슈가 쓴 "strict validation"은 클라이언트 측 스키마
   검사를 뜻하지 Anthropic의 `strict` 도구 플래그가 아니다 — 단어만 겹치는 다른
   것이다.

2. **"v2.0.21이 도입했다"는 귀속은 그 스레드 자체가 뒷받침하지 않고, 이 레포에서
   삭제했다.** 보고자 본인의 후속 코멘트가 v2.0.20도 같은 패키지를 거부했다고
   말하고, 직전 24시간 안에 Perplexity MCP 패키지가 두 번 릴리스됐음을 지적한다 —
   즉 변한 게 클라이언트가 아니라 서버 쪽일 수 있다. 위 #2가 결론을 낸다: 동일한
   400이 **2025-06-27, Claude Code v1.0.35**에서 이미 발생했다. v2.0.21보다 넉 달
   앞이다. 스레드에 Anthropic 엔지니어 응답은 없고 스테일봇이 닫았다.
   `scripts/judge_anthropic.py`와 `../src/lint_anthropic.py`의 독스트링에 있던
   "Claude Code v2.0.21 began forwarding this" 문장은 제거했다.
   **관측된 400 인용은 유지, 버전 귀속은 철회.**

3. **"opt-out이 없다"에 대해: 있고, 도움이 안 된다.** 위 #3이 Claude Code에
   `skipSchemaValidation` 옵션이 존재하며 이 종류의 실패에는 듣지 않는다고 적는다 —
   *"`skipSchemaValidation` in Claude Code only bypasses local validation — the API
   itself still rejects the schema."* 이건 C0의 비-opt-in 분류를 약화시키는 게
   아니라 **강화한다**: 이 데이터셋이 0.0%로 보고하는 축에서는 사용자에게 빠져나갈
   방법이 없다. 그 축들이 깨끗한 축이라는 건 생태계에 다행인 일이다.

#3이 최상위 `anyOf`의 상류 원인으로 지목한 MCP TypeScript SDK 이슈
[#1028](https://github.com/modelcontextprotocol/typescript-sdk/issues/1028),
[#702](https://github.com/modelcontextprotocol/typescript-sdk/issues/702)는
단서로만 적어 둔다. **열어서 확인하지 않았고**, 이 데이터셋의 어떤 것도 거기에
의존하지 않는다.

---

## 검출기는 작동하는가

같은 검출기에서 0.0%와 63.0%가 둘 다 나왔으므로 양쪽 다 증명이 필요하다.

1. **양성 대조군 16/16 검출.** 문서가 축어로 금지한 항목 하나씩만 담은 스키마 16개.
2. **음성 대조군 5/5 통과 — Anthropic 자신의 문서 예제 포함.**
   공식 strict 문서의 `get_weather`·`search_flights`, `pattern` 사용(Anthropic에선 지원),
   `minItems: 1`, 선택 파라미터 정확히 24개(경계). 전부 깨끗하게 통과 → **과검출도 아니다.**
3. **독립 프로덕션 구현이 교차검증.** 공식 Anthropic Python SDK 1.0.0 `transform_schema`를
   14,804개 전부에 돌렸다. 예외 발생 75/617 = 12.2%, 제약 1개 이상 제거 **446/617 = 72.3%**,
   내 정적 C규칙과 서버 단위 일치 510/617 = 82.7%. 키워드별 서버 수도 거의 같다
   (`minimum` 260 vs 267, `maxLength` 131 vs 138 …).
4. **불일치 107건 전부 설명됨.** "FP" 25건 중 **22건**은 `C1-additionalProperties-not-false`,
   나머지 **3건**은 SDK가 제거 단계 전에 예외를 던진 서버다(25건 중 8건이 예외 발생).
   C1 케이스는 규칙 오류가 아니라 오라클의 맹점이다 — SDK는 `additionalProperties`를
   *제거*하지 않고 `false`로 **덮어쓰므로**, 제거 탐지 방식으로는 구조적으로 볼 수 없다.
   "FN" 82건에서 SDK가 잘라낸 것은 `default`(72서버)·`exclusiveMinimum`(4)·`const`(3)·
   `pattern`(2)·`oneOf`(1)인데, 문서는 `default`·`const`·`pattern`을 **지원으로 적었고**
   나머지 둘에는 침묵한다 → 아래 모호성 #4 그 자체다.

---

## 문서화된 모호성 (모든 카운트에서 제외)

문서가 결론을 내리지 않은 지점. 지어내지 않고 `AMB-` 코드로 따로 집계했다.

| # | 코드 | 서버 | 히트 | 왜 모호한가 |
|---|---|---:|---:|---|
| 1 | `AMB-additionalProperties-absent` | **412** | 6,690 | supported 목록은 "must be set to `false` for objects", unsupported 목록은 **비-`false` 값**만 언급. **누락**은 어디에도 없다 |
| 2 | `AMB-numeric:*` | 69 | 380 | "Numerical constraints (**such as** …)" — 목록이 열려 있음 |
| 3 | `AMB-unlisted:*` (`oneOf` 13서버, `propertyNames` 29 …) | 41 | 512 | `anyOf`·`allOf`는 supported로 명시, `oneOf`는 **양쪽 목록 어디에도 없음** |
| 4 | 문서 vs 공식 SDK | — | — | 문서는 `const`·`default`·`pattern`을 supported로 적는데 **공식 SDK는 셋 다 제거**한다. 호출 없이는 판정 불가 |
| 5 | `AMB-format-unlisted:*` | 15 | 110 | 지원 format 10개가 열거돼 있으나 목록 외 format이 400인지 무시인지 미기재 |

**모호성 #1이 헤드라인을 움직인다.** 617개 중 412개에 걸린다. 우리는 보수적 해석
(누락은 위반으로 세지 않음)을 택했다. 다른 해석을 택하면 C가 63.0%에서 **90%대**로 뛴다.
우리는 63.0%와 이 문단을 함께 낸다.

> 412 vs 414: `../REPORT_ANTHROPIC.md` §2는 414로 적는다. 그건 dedup 이전 620행 pooled
> 파일 기준이고, 두 슬라이스에 중복 등장하는 패키지 3개 중 2개가 이 코드를 가진다.
> dedup된 N=617 코퍼스에서는 412다. 판정이 바뀐 건 없다.

---

## 파일

| 파일 | 행 | 1행 = |
|---|---:|---|
| `servers.jsonl` | 617 | 서버 1개: 신원·출처·축별 판정·복잡도 카운터·SDK 오라클 결과·모호 집계 |
| `tools.jsonl` | 14,804 | 도구 1개: 산문 제거된 `inputSchema`/`outputSchema`, 축별 판정과 코드 |
| `violations.jsonl` | 31,954 | 판정 1건: 축·코드·severity·JSON 포인터·원인 값·출처 URL·축어 인용·`repro` 1줄 |
| `controls.jsonl` | 31 | 대조군 1건: 입력·기대 판정·관측 판정·pass/fail |
| `failures.jsonl` | 360 | 기동 실패 서버 1개: 상태·공급한 env 변수 **이름만**·재시도 결과 |
| `STATS.txt` | — | 위 5개 파일에서 재생성한 모든 수치 |

**제3자 산문은 어느 파일에도 없다.** 도구 description과 스키마 내부의
`description`/`title`/`examples` 등을 전부 제거했다 — 총 **4,327,823자**.
그 자리에 `description_len`(정수)과 `description_sha256_12`(12자리)만 남겼다.
구조·프로퍼티 이름·타입·`enum` 값·`pattern` 정규식·판정을 만든 제약 값은 유지한다.
그게 측정 그 자체이기 때문이다.

**산문 제거로 바뀐 판정은 0건이다.** `scripts/verify_verdicts.py`가 제거된 스키마로
판정을 다시 돌려 19,159건을 비교하고 차이 0을 확인한다.

원문 텍스트가 필요하면 직접 재수집하면 된다. `servers.jsonl`에 `package`·`ecosystem`·
`package_version`·`repository`가 전부 들어 있다 (METHODOLOGY.md §7).

---

## 재현

**층 1 — 판정만. 수 초, 네트워크·API 키 불필요.**

```bash
cd dataset
python3 scripts/verify_no_prose.py    # 산문 0 / 자격증명 0 / PII 0
python3 scripts/verify_verdicts.py    # 산문 제거 스키마로 재판정: 차이 0
python3 scripts/stats.py              # README의 모든 수치
python3 scripts/explain.py --help     # 판정 1건씩
```

**층 2 — 수집부터.** 수 시간이고 **임의의 서드파티 코드를 로컬에서 실행**한다.
컨테이너나 일회용 VM에서 돌려라. METHODOLOGY.md 참조.

---

## 한계 (요약)

전체는 [LIMITATIONS.md](LIMITATIONS.md).

1. **API 미호출.** 모든 400은 문서·SDK 동작·공개 관측에서 **예측**한 것이지 관측한 게 아니다.
   공개 관측 7건을 축에 매핑한 것이 [현장 근거](#현장-근거--실제로-400을-맞고-올라온-공개-이슈-7건)이며,
   그중 3건은 어떤 코드에도 대응시키지 못했다.
2. **Go/OCI 서버 미측정.** docker 부재로 약 130개(레지스트리의 2.1%) 제외.
   손으로 스키마를 쓰는 생태계가 바로 거기다. 다만 전부 깨져 있어도 상한이 2.1%다.
3. **기동 실패 360개 미관찰.** `failures.jsonl`에 상태와 함께 기재.
4. **레지스트리는 자기 등록이고 스팸이 있다** (`mcparmory` 37, `CSOAI-ORG` 28, `pulsemcp` 19).
   다만 별·다운로드·도구 수로 걸러도 비율은 **올라간다**(다운로드 ≥1000에서 C=85.0%).
5. **CL 상한은 서버 단독 요청 가정.** 실제 클라이언트는 여러 서버를 섞으므로 37.3%는 하한이다.
6. **모호성 #1 하나가 63.0%를 90%대로 만들 수 있다.**
7. **공식 Anthropic SDK를 쓰는 클라이언트는 이 400을 못 본다.** SDK가 먼저 잘라낸다.
   그 경우 결과는 거부가 아니라 **조용한 검증 상실**이고, 그건 72.3%에서 일어난다.
8. **축 집합이 완전하지 않고, 구멍 하나를 문서화해 뒀다.** Anthropic Messages API는
   property 키에 정규식(`^[a-zA-Z0-9_.-]{1,64}$`)도 강제한다
   ([pylance-release#7986](https://github.com/microsoft/pylance-release/issues/7986)).
   여기 어떤 축도 그걸 검사하지 않는다. 현장 근거 4번 행 참조.

---

## 라이선스 (요약)

- **측정 결과**(우리가 만든 판정 데이터 + 문서) → **CC BY 4.0**
- **스크립트** → **MIT**
- **남의 저작물은 재라이선스하지 않는다.** 서버 작성자의 산문은 애초에 재배포하지 않았고,
  스키마 구조·이름·값은 "이 provider 제약에서 이렇게 처분된다"는 **사실 관찰**로 싣는다.
- 개별 서버의 라이선스 확인 경로(npm/PyPI/repo)는 [LICENSE](LICENSE)에 적었다.

---

## 이 레포의 관련 파일

- `../checker/WIP-HALTED.md` — 서버 작성자용 CLI를 계획했다가 **코드를 한 줄도 쓰기
  전에 중단**한 기록. [선행연구](#선행연구)의 반증 조사에서 같은 영역의 도구 5종이
  이미 있다는 걸 확인했기 때문이다. 무엇을 찾았고 그 결과 무엇을 바로잡았는지 적어 뒀다.
- `../REPORT.md` — 2026-08-09 A·B축 측정 (결과 0.0%, park)
- `../REPORT_ANTHROPIC.md` — 2026-08-23 C축 재측정
- `../sdk-bug/` — `anthropic` 1.0.0 `transform_schema`가 `type: ["string","null"]`에서
  `AssertionError`로 죽는 것을 **직접 작성한** 최소 재현 예제와 이슈 초안.
  **업스트림 제출은 하지 않았다.**
