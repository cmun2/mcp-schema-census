# mcp-schema-census — Anthropic strict 축 재측정 (2026-08-23)

**판정: PUBLISH-WORTH (데이터셋으로. 도구로는 아님.)**

2026-08-09 POC는 **0/620 = 0.0%**로 WORSE park됐다. 그 0%는 두 검증기(MCP TS SDK 파서, openai-agents `ensure_strict_json_schema`)에 대해서만 참이었다.
Anthropic이 출하한 `strict: true` 서브셋을 **같은 코퍼스에 얹은 결과: 389/617 = 63.0%**. 서버 재수집 없이 정적 판정만 했다.

> ⚠️ 이 63.0%는 **"서버가 죽어 있다"가 아니다.** OpenAI 축의 27.6%와 같은 성격 — *naive 클라이언트가 MCP inputSchema를 그대로 `strict:true`로 넘길 때* 400이 나는 비율이다. 이 구분을 흐리면 반박당한다. §5 참조.

참고: 작업 지시서가 가리킨 `out/FIGURES.txt`는 이 레포에 존재하지 않는다(수치는 `REPORT.md`와 `out/*.log`에 있음). 이번 산출물은 `out/THREE_AXIS.txt`.

---

## 1. 3축 비교표

globally de-duplicated by package. **N = 617 서버 / 14,804 도구.**
(기존 REPORT.md의 620은 파일별 dedup 기준. 3개 패키지가 두 슬라이스에 중복 등장한다.)

| 축 | 무엇을 재는가 | 판정자 | 서버 단위 | 도구 단위 |
|---|---|---|---:|---:|
| **A** MCP 사양 적합 (서버 전체 거부) | `client.listTools()`가 throw | 공식 MCP TS SDK `ListToolsResultSchema.safeParse` (실제 프로덕션 파서) | **0/617 = 0.0%** | 0/14,804 = 0.0% |
| **B** OpenAI strict — 하드 거부 | strict 변환 실패 | openai-agents `ensure_strict_json_schema` (실제 프로덕션 변환기) | **170/617 = 27.6%** | 868/14,804 = 5.9% |
| **B′** OpenAI strict — 조용한 검증 상실 | 제약이 무시됨 | 문서화된 미지원 키워드표 | 351/617 = 56.9% | 3,332/14,804 = 22.5% |
| **C0** Anthropic Messages API 기본선 (opt-in 아님) | 루트 `oneOf`/`allOf`/`anyOf` | 관측된 400 (claude-code#10606) | **0/617 = 0.0%** | 0/14,804 = 0.0% |
| **C** Anthropic `strict:true` 서브셋 위반 | 400 | 공식 문서 제약표 (§3), Anthropic Python SDK v1.0.0 `transform_schema`로 교차검증 | **389/617 = 63.0%** | **3,411/14,804 = 23.0%** |
| **CL** Anthropic 요청 복잡도 상한 | 400 | 공식 문서 explicit limits 표 | **230/617 = 37.3%** | n/a (요청 단위 지표) |
| **C\*** Anthropic 어느 하나라도 | | | **447/617 = 72.4%** | 3,411/14,804 = 23.0% |

### 모집단별 (holdout은 A·B 규칙 확정 *후* 수집된 분리 슬라이스)

| 모집단 | N | A | B | C0 | C | CL | C* |
|---|---:|---:|---:|---:|---:|---:|---:|
| npm | 298 | 0.0% | 26.2% | 0.0% | 62.8% | 38.6% | 73.5% |
| PyPI | 117 | 0.0% | 42.7% | 0.0% | 53.8% | 41.9% | 63.2% |
| npm **holdout** | 202 | 0.0% | 20.8% | 0.0% | **68.8%** | 32.7% | 76.2% |

holdout이 튜닝셋보다 오히려 높다. C는 슬라이스 의존적이지 않다.

### 활성 부분집합 — **스팸 인플레가 아니다. 반대다.**

| 부분집합 | N | C | CL | C* |
|---|---:|---:|---:|---:|
| 전체 | 617 | 63.0% | 37.3% | 72.4% |
| GitHub repo 있음 | 354 | 59.6% | 39.5% | 70.1% |
| ★ ≥ 10 | 87 | 59.8% | **58.6%** | **77.0%** |
| ★ ≥ 100 | 11 | 54.5% | 45.5% | 72.7% |
| 도구 ≥ 5개 | 450 | 66.4% | 50.0% | 78.9% |
| npm 주간 다운로드 ≥ 1000 | 20 | **85.0%** | 65.0% | **85.0%** |

진짜로 쓰이는 서버일수록 **더** 위반한다. 스키마가 풍부할수록 제약 키워드가 많기 때문이다.

---

## 2. 위반 유형별 분포 (pooled, 620행 기준 원자료)

| 코드 | 위반 | 서버 수 | 도구 히트 |
|---|---|---:|---:|
| `C2-numeric-constraint:minimum` | `minimum` | 268 | 2,837 |
| `C2-numeric-constraint:maximum` | `maximum` | 260 | 2,385 |
| `C3-string-constraint:minLength` | `minLength` | 158 | 2,369 |
| `C1-additionalProperties-not-false` | `additionalProperties` ≠ false | 170 | 1,706 |
| `C3-string-constraint:maxLength` | `maxLength` | 138 | 1,409 |
| `C4-array-constraint:maxItems` | `maxItems` | 94 | 296 |
| `C6-recursive-schema` | 재귀 스키마 | 5 | 63 |
| `C4-array-constraint:minItems` | `minItems` ≥ 2 | 24 | 32 |
| `C8-allOf-with-ref` | `allOf` + `$ref` | 1 | 11 |
| `C4-array-constraint:uniqueItems` | `uniqueItems` | 1 | 6 |

| 요청 상한 | 서버 수 |
|---|---:|
| `CL2` 선택 파라미터 > 24 | 211 |
| `CL1` strict 도구 > 20 | 142 |
| `CL3` union 타입 파라미터 > 16 | 18 |

**핵심:** B축을 지배한 원인은 `additionalProperties`(단일 원인 99.9%)였다. **C축의 지배 원인은 그게 아니라 `minimum`/`maximum`/`minLength`/`maxLength`** — B축에서는 *조용히 버려지던* 키워드들이다. 이것이 두 축이 겹치지 않는 이유다.

### 모호 판정 (문서가 결론을 안 내리는 것 — 지어내지 않고 별도 집계)

| 코드 | 서버 | 히트 | 왜 모호한가 |
|---|---:|---:|---|
| `AMB-additionalProperties-absent` | 414 | 6,709 | supported 목록은 "must be set to `false` for objects", 그러나 unsupported 목록은 **비-false 값**만 언급. **누락**이 400인지 명시 없음 |
| `AMB-numeric:exclusiveMinimum` | 69 | 379 | "such as minimum, maximum, multipleOf" — 목록이 열려 있음 |
| `AMB-unlisted:oneOf` | 13 | 329 | `anyOf`/`allOf`는 supported로 명시, `oneOf`는 **양쪽 목록 어디에도 없음** |
| `AMB-unlisted:propertyNames` | 29 | 165 | 동일 |
| `AMB-format-unlisted:*` | 15 | 110 | 지원 format 10개가 열거돼 있으나 목록 외 format이 400인지 무시인지 미기재 |
| `AMB-unlisted:not / if / then / minProperties / dependentRequired` | 1–2 | 1–7 | 동일 |

`AMB-additionalProperties-absent`가 414/617에 걸린다는 점이 중요하다. **문서 한 줄의 해석에 따라 C가 63%에서 90%대로 뛴다.** 이 모호성 자체가 데이터셋이 보고할 값이다.

---

## 3. Anthropic strict 제약 표 (출처 URL 필수)

전부 아래 두 문서에서 **축어 인용**. 원문은 `curl https://platform.claude.com/docs/en/build-with-claude/structured-outputs.md`로 재확인 가능(Mintlify `.md` 엔드포인트, 무인증).

**출처**
- [S1] https://platform.claude.com/docs/en/agents-and-tools/tool-use/strict-tool-use — `strict: true`를 툴 정의 최상위에 설정. *"The schema uses standard JSON Schema format with some limitations"* → 제약 목록은 [S2]로 위임.
- [S2] https://platform.claude.com/docs/en/build-with-claude/structured-outputs#json-schema-limitations — *"Structured outputs support standard JSON Schema with some limitations. **Both JSON outputs and strict tool use share these limitations.**"*
- [S3] https://platform.claude.com/docs/en/build-with-claude/structured-outputs#schema-complexity-limits — explicit limits 표.
- [S4] https://github.com/anthropics/claude-code/issues/10606 — **관측된** 400 (문서에 없음).
- [S5] `anthropic` Python SDK v1.0.0, `anthropic/lib/_parse/_transform.py` — 공식 SDK가 실제로 무엇을 잘라내는가.

### 3-1. 거부(400) — 문서가 명시

> [S2] "If you use an unsupported feature, you'll receive a **400 error with details**."

| # | 제약 (축어) | 출처 |
|---|---|---|
| C1 | "`additionalProperties` set to anything other than `false`" | [S2] Not supported |
| C2 | "Numerical constraints (such as `minimum`, `maximum`, `multipleOf`)" | [S2] |
| C3 | "String constraints (`minLength`, `maxLength`)" | [S2] |
| C4 | "Array constraints beyond `minItems` of 0 or 1" (→ `maxItems`, `uniqueItems`, `minItems`≥2) | [S2] |
| C5 | "External `$ref` (for example, `'$ref': 'http://...'`)" | [S2] |
| C6 | "Recursive schemas" | [S2] |
| C7 | "Complex types within enums" | [S2] |
| C8 | "`anyOf` and `allOf` (with limitations — **`allOf` with `$ref` not supported**)" | [S2] Supported features |

### 3-2. 요청 단위 상한 (400) — [S3] 표 축어

| 한도 | 값 | 원문 |
|---|---:|---|
| CL1 Strict tools per request | **20** | "Maximum number of tools with `strict: true`. Non-strict tools don't count toward this limit." |
| CL2 Optional parameters | **24** | "Total optional parameters across all strict tool schemas and JSON output schemas. **Each parameter not listed in `required` counts toward this limit.**" |
| CL3 Parameters with union types | **16** | "Total parameters that use `anyOf` or type arrays (for example, `\"type\": [\"string\", \"null\"]`) across all strict schemas." |

> [S3] Note: "These limits apply to the **combined total across all strict schemas in a single request**."
> 추가로 문서화되지 않은 내부 상한이 있고, 초과 시 400 `"Schema is too complex for compilation."` / 컴파일 타임아웃 180초.

### 3-3. 지원됨 — OpenAI strict와 **다른** 지점

| 키워드 | Anthropic | OpenAI strict |
|---|---|---|
| `pattern` (정규식) | **지원.** [S2]에 "Pattern support (regex)" 전용 절이 있고, backreference·lookahead·`\b`·큰 `{n,m}`만 미지원 | 조용히 무시 |
| 선택 파라미터 (`required` 미포함) | **지원** (단 총 24개 상한) | `required`에 전 속성 나열 강제 |
| `minItems` 0 또는 1 | 지원 | 무시 |
| 지원 string format | `date-time, time, date, duration, email, hostname, uri, ipv4, ipv6, uuid` **10개로 열거** | `format` 전부 무시 |

### 3-4. 명시적으로 모호한 지점 (지어내지 않음)

1. **`additionalProperties` 누락.** supported 목록은 "must be set to `false` for objects"라 쓰지만, unsupported 목록은 "set to anything other than `false`"만 든다. 누락이 400인지 문서에 없다. SDK는 항상 `false`를 **추가**한다([S5] "Add `additionalProperties: false` to all objects"). → 617중 414서버에 걸리는 축이라 결론을 바꾼다.
2. **`oneOf`.** supported에도 unsupported에도 없다. SDK는 `oneOf`를 `anyOf`로 **재작성**한다([S5]).
3. **열거되지 않은 `format` 값.** 400인지 무시인지 미기재. SDK는 잘라내 description에 붙인다.
4. **문서 vs 구현 불일치.** 문서는 `const`·`default`·`pattern`을 supported로 적는데, **공식 Python SDK는 셋 다 wire 스키마에서 제거해 description 문자열에 붙인다**([S5] 확인). 어느 쪽이 API의 진짜 동작인지는 호출 없이는 판정 불가(이번 라운드 NO-SPEND).
5. **C0 (루트 `oneOf`/`allOf`/`anyOf`)은 공개 제약 문서에 없다.** [S4]의 관측된 400 문자열 `"tools.XX.custom.input_schema: input_schema does not support oneOf, allOf, or anyOf at the top level"`이 유일한 근거다. 표에 EMPIRICAL로 표기했다.

---

## 4. 자기 공격

### 4-1. 양성 대조군 — **검출기는 작동한다 (16/16 + 5/5)**

`src/ctrl_anthropic.py`. 양성 케이스는 문서가 축어로 금지한 것 또는 [S4]의 관측 400만 사용. 음성 케이스는 **Anthropic 자신의 문서 예제**.

| 케이스 | 기대 | 결과 |
|---|---|---|
| 루트 `anyOf` / `oneOf` / `allOf` (3건) | C0 | ✅ 검출 |
| `minimum` / `multipleOf` | C | ✅ |
| `minLength` | C | ✅ |
| `maxItems` / `minItems:2` | C | ✅ |
| `additionalProperties: {type:string}` | C | ✅ |
| 외부 `$ref` (http) | C | ✅ |
| 재귀 `$defs` 순환 | C | ✅ |
| enum 안에 객체 | C | ✅ |
| `allOf` + `$ref` | C | ✅ |
| 선택 파라미터 25개 | CL | ✅ |
| strict 도구 21개 | CL | ✅ |
| union 파라미터 17개 | CL | ✅ |
| **DOC `get_weather`** (Anthropic 공식 strict 예제) | clean | ✅ 통과 |
| **DOC `search_flights`** (공식 예제, `format:date` + integer enum) | clean | ✅ 통과 |
| `pattern` 사용 (Anthropic에선 지원) | clean | ✅ 통과 — **FP 아님** |
| `minItems: 1` | clean | ✅ 통과 |
| 선택 파라미터 정확히 24개 (경계) | clean | ✅ 통과 |

**양성 16/16, 음성 5/5.** 0%가 아니라 63%가 나온 것이 검출기 오작동이 아님을, 그리고 **역방향 오작동(과검출)도 아님**을 Anthropic 자신의 예제로 확인했다.

기존 POC의 대조군 10건(MCP 사양 위반 계열)을 C축에 넣으면 대부분 통과한다 — 당연하다. bare `true`나 `type` 누락은 *MCP 사양* 위반이지 *Anthropic strict* 위반이 아니다. **대조군은 축마다 달라야 한다**는 것이 이번에 확인된 방법론적 교훈이다.

### 4-2. 독립 프로덕션 오라클 — 공식 Anthropic Python SDK v1.0.0

내 규칙을 믿지 않기 위해, 문서를 읽고 만든 규칙과 **별개로** 공식 SDK의 실제 변환 코드
(`anthropic/lib/_parse/_transform.py::transform_schema`)를 14,804개 스키마 전부에 돌렸다.
SDK가 wire 스키마에서 **잘라낸 키워드 집합** = SDK 작성자가 미지원으로 간주하는 집합.

| 지표 | 값 |
|---|---:|
| `transform_schema`가 **예외를 던짐** (정규화조차 불가) | **75/617 = 12.2%** |
| `transform_schema`가 제약을 **1개 이상 제거** | **446/617 = 72.3%** |
| 내 정적 C규칙과의 서버 단위 일치 | 510/617 = 82.7% |

SDK가 실제로 제거한 키워드(서버 수) — 내 규칙 집계와 나란히 놓으면:

| 키워드 | SDK가 제거한 서버 | 내 규칙이 잡은 서버 |
|---|---:|---:|
| `minimum` | 260 | 268 |
| `maximum` | 253 | 260 |
| `minLength` | 154 | 158 |
| `maxLength` | 131 | 138 |
| `maxItems` | 87 | 94 |
| `exclusiveMinimum` | 64 | 69 (AMB) |
| `minItems` | 19 | 24 |
| `uniqueItems` | 1 | 1 |

**독립 구현이 같은 키워드를, 거의 같은 서버 수에서 제거한다.** 내가 프로즈를 잘못 읽은 게 아니다.

불일치 107건은 둘 다 실제 오류가 아니다:
- **"FP" 25건** — 전부 `C1-additionalProperties-not-false`(74히트)와 SDK가 먼저 예외를 던진 8건. SDK는 `additionalProperties`를 *제거*하지 않고 `false`로 **덮어쓴다**. 오라클의 "drop" 탐지가 구조상 못 잡는 케이스지 내 규칙의 오검출이 아니다.
- **"FN" 82건** — SDK가 잘라낸 `default`(323) / `exclusiveMinimum`(5) / `const`(5) / `pattern`(4) / `oneOf`(1). 이들은 문서가 **supported로 적었거나**(default·const·pattern) 침묵한다(exclusiveMinimum·oneOf). 내 규칙이 문서를 따라 일부러 침묵한 것 — §3-4의 문서/구현 불일치 그 자체다.

### 4-3. 공식 SDK의 실제 크래시 (부수 발견)

`transform_schema`가 던진 예외 (도구 단위):

| 예외 | 건수 | 원인 |
|---|---:|---|
| `ValueError: Schema must have a 'type', 'anyOf', 'oneOf', or 'allOf' field.` | 150 | 타입 없는 노드 |
| `AssertionError: Expected code to be unreachable, but got: ['string','null']` | 57 | **nullable 타입 배열** |
| 동일, `['integer','null']` / `['number','null']` / `['string','number']` 등 | 30 | 동일 |
| `TypeError: 'list' object is not a mapping` | 6 | 튜플형 `items` |

`type: ["string","null"]`은 zod `.nullable()` / pydantic `Optional[...]`이 흔히 뱉는 형태다. 공식 SDK의 `assert_never`가 그걸 막지 못하고 **AssertionError로 죽는다**. 문서화된 제약이 아니라 구현 결함으로 보이며, 이 코퍼스가 없었으면 발견되지 않았을 종류의 사실이다.

### 4-4. 축 간 중복/독립 — **독립이다**

| | C* 실패 | C* 통과 |
|---|---:|---:|
| **B 실패** | 170 | **0** |
| **B 통과** | **277** | 170 |

- Jaccard(B, C\*) = **0.380**
- P(C\* \| B) = **1.000** — OpenAI strict에서 깨지는 서버는 **예외 없이** Anthropic에서도 깨진다 (B ⊂ C\*)
- P(B \| C\*) = **0.380** — 역은 성립하지 않는다
- **양쪽 기존 축(A·B)에서 깨끗한데 Anthropic 축에서 깨지는 서버: 277/617 = 44.9%** ← 2026-08-09 POC가 못 본 정보
- **OpenAI에서는 "조용한 상실"에 그쳤는데 Anthropic에서는 하드 400인 서버: 219/617 = 35.5%** ← 결정적 비대칭

즉 세 축은 **포함관계 사슬**이다: A(0%) ⊂ B(27.6%) ⊂ C\*(72.4%). 축을 늘린 의미가 있다. 다만 **B가 C에 완전히 포함되므로 B를 따로 낼 필요는 없다** — B는 C의 부분집합으로 보고하면 된다.

같은 키워드에 대한 두 provider의 처분이 갈리는 지점이 원인이다:

| 키워드 | OpenAI strict | Anthropic strict |
|---|---|---|
| `additionalProperties` ≠ false | 400 | 400 |
| `minimum` / `maximum` | **조용히 제거** | **400** |
| `minLength` / `maxLength` | **조용히 제거** | **400** |
| `maxItems` / `uniqueItems` | **조용히 제거** | **400** |
| `minItems` ≥ 2 | 조용히 제거 | 400 |
| `pattern` | 조용히 제거 | **지원** |
| 선택 파라미터 > 24 | 그런 상한 없음 | **400** |
| strict 도구 > 20 | 그런 상한 없음 | **400** |

---

## 5. 이 63%가 무엇이 **아닌지** (억지로 크게 만들지 않기)

정직하게 적는다. 이 수치의 한계는 헤드라인만큼 중요하다.

1. **`strict: true`는 opt-in이고 도구 단위다.** 서버가 "죽어 있는" 게 아니라, *클라이언트가 그 도구에 strict를 켜면* 400이 난다. A축(0%)만이 opt-in이 아닌 축이었고, C0(0%)도 opt-in이 아닌데 **역시 0%**다. **비-opt-in 축에서는 여전히 0%다** — 이건 2026-08-09 결론과 일치하며 뒤집히지 않았다.
2. **공식 SDK를 쓰는 클라이언트는 400을 안 본다.** `transform_schema`가 미지원 키워드를 잘라 description에 붙인다. 그 경우 결과는 400이 아니라 **조용한 검증 상실**이고, 그건 72.3%에서 일어난다. B축에서 봤던 상류 방어와 같은 구조다.
3. **API를 호출해 확인하지 않았다.** NO-SPEND 제약. 판정 근거는 ① 공식 문서의 축어 제약 ② 공식 SDK 구현 ③ 관측된 400 리포트다. 실제 400 여부의 end-to-end 확인은 미측정이며, 데이터셋에 그렇게 표기해야 한다.
4. **CL 상한은 서버 단독 요청을 가정한다.** 실제 요청은 여러 서버의 도구를 섞으므로 실사용에서는 **더 쉽게** 초과된다. 즉 37.3%는 하한이다.
5. **§4-1의 미측정 구멍은 그대로다** — docker 필요 Go/OCI 서버 130개, 기동 실패 360개.
6. **문서 모호성 하나가 63% → 90%대를 가른다** (`additionalProperties` 누락, 414서버). 이 축은 보수적으로 잡았다.

---

## 6. 실제 예시 — 위반 스키마 조각과 고칠 3~5줄

### (a) `@burtthecoder/mcp-virustotal` (★144) — **여기서는 "3~5줄 수정"이 진짜로 성립한다**

`get_url_relationship.inputSchema`:
```json
"limit": { "type": "number", "minimum": 1, "maximum": 40, "default": 10 }
```
`minimum`/`maximum` → [S2] "Numerical constraints" → 400. 7개 도구 중 3개가 동일 패턴.

고침 (zod 3줄):
```diff
- limit: z.number().min(1).max(40).default(10)
+ limit: z.number().default(10)
+   .describe('Number of results. Must be between 1 and 40.')  // 제약을 설명으로 이관
+ // 서버 핸들러에서 런타임 검증: if (limit < 1 || limit > 40) throw new Error(...)
```
이것이 candidate가 약속했던 "의미 보존 강등"이고, **C축에서는 실제로 필요하다.** (B축에서는 §4 REPORT.md대로 성립하지 않았다.)

### (b) `chrome-devtools-mcp` (★48,797, 공식 Chrome DevTools) — 29개 도구 전부

```json
{ "type": "object",
  "properties": { "uid": {"type":"string"}, "dblClick": {"type":"boolean"} },
  "required": ["uid"],
  "additionalProperties": true,          // ← [S2] "set to anything other than false"
  "$schema": "http://json-schema.org/draft-07/schema#" }
```
`additionalProperties: true`가 **명시적으로** 들어가 있다. 고침은 1줄(`true` → `false`), 도구 29개 전부에 적용. 이 서버는 **B축·C축 양쪽에서 깨진다.** 추가로 도구 29 > 20, 선택 파라미터 초과로 CL1·CL2도 위반.

### (c) `com.mux/mcp` (★179, 공식 Mux) — **서버가 고칠 수 없는 종류**

도구 98개, 최상위 선택 파라미터 합계 **290개** (상한 24).
CL1(도구 20) · CL2(선택 24) 동시 위반. 스키마를 어떻게 고쳐도 이 서버의 도구 전체를 한 요청에 strict로 넣을 수 없다.
→ 고쳐야 할 주체는 서버가 아니라 **클라이언트**(도구 일부만 strict로 표시)다. 데이터셋이 알려줄 수 있는 것은 "어느 서버가 이 범주인가"다.

### (d) `zotero-mcp` (★4,580)
도구 37개, `additionalProperties`≠false 7건 + CL1·CL2·**CL3(union 타입 파라미터 >16)** 전부 위반. CL3를 때리는 유일한 상위 서버.

---

## 7. 판정

**PUBLISH-WORTH — 단, "도구"가 아니라 `mcp-schema-census` 데이터셋으로만.**

근거:
1. **재검토 트리거가 실제로 결과를 뒤집었다.** 0.0% → 63.0%(strict 서브셋) / 72.4%(어느 하나라도). park 임계 5%를 크게 넘는다.
2. **새 정보가 44.9%다.** 기존 두 축에서 깨끗한데 Anthropic 축에서 깨지는 서버. 축을 늘린 것이 중복이 아니었음이 수치로 확인된다(Jaccard 0.380, B ⊊ C\*).
3. **검출기가 작동함을 양방향으로 증명했다** (양성 16/16, 음성 5/5, 음성은 Anthropic 자신의 예제).
4. **독립 프로덕션 구현이 교차검증한다** (공식 Anthropic SDK v1.0.0, 키워드별 서버 수가 거의 일치).
5. **그럼에도 도구는 만들면 안 된다** — candidate 재검토가 실측했듯 MCP 적합성 도구는 4번 시도돼 전부 0~2★. 채택 경로가 죽어 있다.

**PUBLISH-WORTH가 아닌 것으로 볼 수 있는 반론과 그에 대한 답:**
- *"opt-in 모드 숫자라 임팩트가 약하다"* — 맞다. 그래서 헤드라인은 "생태계가 깨져 있다"가 아니라 **"세 축의 판정이 서로 다르고, 그 차이가 44.9%다"**여야 한다. 그건 그 자체로 인용 가능한 사실이다.
- *"그럼 A=0%, C0=0%가 진짜 헤드라인 아닌가"* — 그것도 데이터다. **비-opt-in 축에서는 생태계가 깨끗하고, opt-in strict 축에서만 63~72%가 깨진다**는 대비가 이 데이터셋의 실제 발견이다. 아무도 이 대비를 공개한 적이 없다.

---

## 8. 재현

```bash
# 축 C 판정 (서버 재수집 불필요, 수 초)
python3 src/lint_anthropic.py data/tools_stdio.jsonl          data/anth_npm.jsonl
python3 src/lint_anthropic.py data/tools_pypi.jsonl           data/anth_pypi.jsonl
python3 src/lint_anthropic.py data/tools_stdio_holdout.jsonl  data/anth_holdout.jsonl

# 대조군 (양성 16 + 음성 5)
python3 src/ctrl_anthropic.py

# 독립 오라클: 공식 Anthropic SDK 변환기
uv venv .venv-anth --python 3.12 && uv pip install --python .venv-anth/bin/python anthropic
.venv-anth/bin/python src/oracle_anthropic_sdk.py \
    data/tools_stdio.jsonl data/tools_pypi.jsonl data/tools_stdio_holdout.jsonl data/oracleC_sdk.jsonl

# 3축 비교 + 독립성 분석
python3 src/analyze3.py | tee out/THREE_AXIS.txt

# 제약 원문 재확인 (무인증, 무료)
curl -sL https://platform.claude.com/docs/en/build-with-claude/structured-outputs.md | sed -n '2815,2975p'
```

외부 usage-based API 호출: **0회.** LLM provider 호출 없음. 서버 재기동 없음.

---

## 9. 소요 시간

약 75분 (상한 90분). 문서 제약 확정 20분, 판정기·대조군 작성 25분, 오라클·독립성 분석 15분, 보고 15분.
