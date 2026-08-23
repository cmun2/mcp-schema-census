# mcp-schema-compat — 3시간 falsification POC 결과

**판정: WORSE. 즉시 park.**

사전 등록 가설: *"공개 MCP 서버 N≥60의 `tools/list` 스키마 중 **20% 이상**이 strict 클라이언트에서 **서버 전체가 거부**된다."*
합격선: ≥20% 지지 / **<5% 즉시 park**.

**실측: 0/620 = 0.0%.** park 임계(5%)의 아래, 그것도 바닥이다.

---

## 1. 실측 수치

주 지표 = **"spec을 지키는 MCP 클라이언트에서 `client.listTools()`가 throw해서 그 서버의 도구가 전부 사용 불가가 되는가."**
판정은 내 코드가 아니라 **공식 MCP TypeScript SDK(v1.30.0)의 진짜 파서** `ListToolsResultSchema.safeParse()`가 내렸다.

| 모집단 | 수집 방식 | N | **A: 서버 전체 거부** | B: OpenAI strict 변환 실패 |
|---|---|---:|---:|---:|
| npm (레지스트리 무작위) | 로컬 `npx` stdio 기동 | 298 | **0/298 = 0.0%** | 78/298 = 26.2% |
| PyPI (레지스트리 무작위) | 로컬 `uvx` stdio 기동 | 118 | **0/118 = 0.0%** | 50/118 = 42.4% |
| npm **holdout** (분리 슬라이스) | 로컬 `npx` stdio 기동 | 204 | **0/204 = 0.0%** | 43/204 = 21.1% |
| **POOLED** | | **620** | **0/620 = 0.0%** | 171/620 = 27.6% |

수집 총계: 서버 **620개**, 도구 **14,000+개**의 실제 `tools/list` 응답.

---

## 2. 사전 등록 대비 실측 차이

### baseline (사전 선언대로 다시 적는다)
> "공개 수치 부재. 선행 연구 Specmatic은 N=3에 백분율 없음. 즉 이 숫자 자체가 기여다."

이 baseline은 **그대로 유효했다.** 실제로 공개된 백분율은 없었고, 이 POC가 N=620으로 처음 측정했다.
다만 **기여의 방향이 반대**다. "생태계가 X% 깨져 있다"가 아니라 **"깨져 있지 않다"**가 결과다.

### "맞혔을 때 사용자가 얻는 것" (사전 선언대로 다시 적는다)
> "스키마 3~5줄을 고쳐 서버 전체를 죽음에서 되살리는 **이산 스위치**(금액이 아니라 동작/비동작)."

**이 이산 스위치는 실측에서 발견되지 않았다.** 620개 서버 중 죽어 있는 서버가 0개다. 되살릴 대상이 없다.

### 왜 빗나갔는가 — 근거로 삼았던 버그 리포트들이 전부 "이미 고쳐진 과거"였다

후보 정의가 인용한 증거는 실재했지만, **전부 2025년 사건이고 전부 상류에서 해소됐다.**

1. **스키마를 사람이 안 쓴다.** npm 서버는 사실상 100% 공식 TypeScript SDK를 쓰고, SDK가 zod에서 `inputSchema`를 **생성**한다. `type: "object"`가 사람 손을 안 거치므로 위반이 **표현 불가능**하다. PyPI도 FastMCP가 pydantic에서 생성한다. 인용된 위반 사례(`github-mcp-server`의 Go `interface{}`발 bare `true`)는 **손으로 스키마를 쓰는 Go 생태계**의 것이고, Go 서버는 OCI 이미지로 배포되어 이 환경(docker 없음)에서 측정하지 못했다 — **이것이 이 POC의 가장 큰 미측정 구멍이다(§6).**
2. **strict 변환이 기본값이 아니다.** OpenAI Agents SDK: `convert_schemas_to_strict = self.mcp_config.get("convert_schemas_to_strict", False)` — **기본 False.** MCP 도구는 기본적으로 strict 변환을 아예 거치지 않는다.
3. **켜도 서버가 안 죽는다.** 켠 경우에도 `to_function_tool`이 `ensure_strict_json_schema` 실패를 **도구 단위로 try/except해서 non-strict로 강등**한다. 소스 주석이 명시한다: *"Convert a separate copy so the non-strict fallback keeps..."* → 서버 전체 거부가 아니라 **그 도구 하나가 strict 보장만 잃는다.**

즉 후보의 핵심 증폭 논리("스키마 하나가 서버 전체를 죽인다")는 **2026년 8월 기준 상류에서 이미 방어됐다.**

---

## 3. strict 제약 표 (출처 URL 필수)

### 규칙군 A — MCP 사양 준수. **서버 전체 치명적.**

| # | 위반 | 사양 근거 |
|---|---|---|
| A1 | `inputSchema` 부재 | `Tool.required = ["inputSchema","name"]` |
| A2 | `inputSchema`가 객체가 아님 (Go `interface{}`발 bare `true`) | 동일 |
| A3 | `inputSchema.type != "object"` (부재 / `"string"` / `["object","null"]`) | `inputSchema.properties.type = {"const":"object"}` |
| A4 | `required`가 문자열 배열이 아님 (`null` 포함) | `required: z.array(z.string()).optional()` |
| A5 | `name` 부재/비문자열 | `Tool.required` |
| A6 | `outputSchema.type != "object"` | `outputSchema` 동일 제약 |

출처:
- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/schema/2025-06-18/schema.json
- https://github.com/modelcontextprotocol/typescript-sdk/blob/main/packages/core-internal/src/wire/rev2025-11-25/buildSchemas.ts
- https://modelcontextprotocol.io/specification/2025-06-18/server/tools
- https://github.com/modelcontextprotocol/inspector/issues/1005 (공식 Inspector가 이 검증을 안 한다고 인정)

**증폭 메커니즘 (소스로 확인):**
```ts
const ListToolsResultSchema = PaginatedResultSchema.extend({ tools: z.array(ToolSchema) })
```
`z.array()`는 **하나라도 실패하면 배열 전체 파스가 실패**한다 → `client.listTools()`가 throw → **그 서버의 도구가 0개가 된다.** 후보가 주장한 이산 스위치는 **메커니즘으로는 실재한다.** 다만 그 스위치를 당기는 서버가 620개 중 0개였다.

### 규칙군 B — OpenAI strict mode. **도구 단위(현행 SDK), 서버 전체 아님.**

| # | 위반 | 근거 |
|---|---|---|
| B1 | 루트 `anyOf` | "Root objects can't be the `anyOf` type" |
| B2 | 루트가 nullable/non-object | `_ensure_strict_root` |
| B3 | 객체의 `additionalProperties`가 `false`가 아님 | "Always set `additionalProperties: false` in objects" |
| B4 | `type` 없고 `additionalProperties` truthy | `_ADDITIONAL_PROPERTIES_ERROR` |
| B5 | 미지원 키워드 (조용한 검증 상실) | `minLength maxLength pattern format` / `minimum maximum multipleOf` / `patternProperties unevaluatedProperties propertyNames minProperties maxProperties` / `unevaluatedItems contains minContains maxContains minItems maxItems uniqueItems` |
| B6 | 속성 100개 초과 / 중첩 5단계 초과 | "up to 100 object properties total, with up to five levels of nesting" |

출처:
- https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/structured-outputs
- https://github.com/openai/openai-agents-python/blob/main/src/agents/strict_schema.py
- https://github.com/openai/openai-agents-python/blob/main/src/agents/mcp/util.py

---

## 4. 위반 유형별 분포와 실제 예시

### A (서버 전체 거부): **분포 없음. 620개 중 0건.**

### B (OpenAI strict 변환 실패): 도구 단위 870건, 서버 단위 171/620

| 원인 | 도구 건수 |
|---|---:|
| `additionalProperties`가 `false`가 아님 | **869 (99.9%)** |
| `$ref` 해석 실패 | 1 |

B는 사실상 **단일 원인**이다. 그리고 그 원인은 대부분 **버그가 아니라 표현력 한계**다 — `z.record(z.string(), z.string())`(= 자유 키 딕셔너리)가 `additionalProperties: {"type":"string"}`으로 나오는데, strict mode에는 **열린 딕셔너리를 표현할 방법이 없다.**

실제 예시 (별 많은 순):

| 서버 | ★ | 도구 | 위반 지점 |
|---|---:|---|---|
| `chrome-devtools-mcp` | 48,797 | `click` | `additionalProperties` ≠ false |
| `zotero-mcp-server` | 4,580 | `zotero_search_items` | 동일 |
| `@sveltejs/mcp` | 305 | `playground-link` | 동일 |
| `aws-dynamodb-mcp-server` | 76 | `get_item` | 동일 |

**"고칠 3~5줄"이 성립하는가 — 아니다.** 예: `@abhishekmcp/http`의 `#/properties/headers`가 `{"type":"string"}`(임의 헤더 맵). 이걸 strict에 맞추려면
```json
"headers": { "type": "object", "additionalProperties": false,
             "properties": { /* 헤더 이름을 전부 하드코딩해야 함 */ } }
```
즉 **3~5줄 수정이 아니라 기능 자체를 포기하는 것**이다. 고쳐야 할 쪽은 서버가 아니라 클라이언트의 강등 로직이고, **그 강등 로직은 이미 상류에 구현돼 있다.**

---

## 5. 자기 공격 결과

### 5-1. 모집단 편향 점검 — **A의 0%는 어떤 부분집합에서도 안 깨진다**

| 부분집합 | N | A | B |
|---|---:|---:|---:|
| 전체 | 620 | **0.0%** | 27.6% |
| GitHub repo 있음 | 315 | **0.0%** | 31.7% |
| ★ ≥ 10 | 83 | **0.0%** | 43.4% |
| ★ ≥ 100 | 11 | **0.0%** | 45.5% |
| npm 주간 다운로드 ≥ 1000 | 20 | **0.0%** | 50.0% |
| 2026년에 커밋됨 (활성) | 309 | **0.0%** | 32.0% |
| fork 아님 | 315 | **0.0%** | 31.7% |
| 도구 ≥5개 (장난감 아님) | 453 | **0.0%** | 33.3% |
| **GitHub owner당 1개로 dedup** (템플릿 fork/스팸 퍼블리셔 제거) | 478 | **0.0%** | 26.2% |

스팸 퍼블리셔는 실재했다(`mcparmory` 37개, `CSOAI-ORG` 28개, `pulsemcp` 19개). owner당 1개로 줄여도 A=0.0%로 동일.
**B는 활성 서버에서 오히려 올라간다**(★≥10에서 43.4%, 다운로드≥1000에서 50.0%) → B는 스팸 인플레가 아니라 진짜다. 다만 §4대로 B는 "고칠 수 있는 결함"이 아니다.

### 5-2. holdout — 통과
제약 표를 확정한 **뒤에** 수집한 분리 슬라이스(npm offset 420+, N=204)에서 A=**0.0%**, B=21.1%. 튜닝셋과 일치.

### 5-3. 오판정 점검 — **3중으로 했다**

**(a) 자동 판정 vs 진짜 프로덕션 검증기** (내 정적 규칙 vs 공식 SDK 파서 / OpenAI 실제 변환기):

| 모집단 | 규칙 | N | FP | FN | 오판정률 |
|---|---|---:|---:|---:|---:|
| npm | A | 298 | 0 | 0 | **0.0%** |
| pypi | A | 118 | 0 | 0 | **0.0%** |
| holdout | A | 204 | 0 | 0 | **0.0%** |
| npm | B | 298 | 6 | 0 | 2.0% |
| pypi | B | 118 | 1 | 0 | 0.8% |
| holdout | B | 204 | 3 | 1 | 2.0% |

**헤드라인 수치는 내 규칙이 아니라 oracle(공식 SDK 파서)이 낸 것**이므로 이 오판정률은 헤드라인에 영향이 없다.

**(b) 양성 대조군 — 0%가 "검출기가 죽어서" 나온 게 아님을 증명.**
실제 버그 리포트에서 가져온 알려진 불량 스키마 10개를 주입:

| 대조군 | oracle A가 잡았나 |
|---|---|
| bare `true` (Go `interface{}`) | ✅ throw |
| `type` 누락 | ✅ throw |
| `type: ["object","null"]` | ✅ throw |
| `inputSchema` 부재 | ✅ throw |
| `required: null` (opencode#35528) | ✅ throw |
| `type: "string"` 루트 | ✅ throw |
| `outputSchema.type: "array"` | ✅ throw |
| 루트 `anyOf` (A 아님) | ✅ 통과(정상) |
| `additionalProperties: true` (A 아님) | ✅ 통과(정상) |
| 정상 스키마 (음성 대조) | ✅ 통과(정상) |

**7/7 검출, 3/3 정상 통과.** 검출기는 살아 있다. **0%는 진짜다.**

이 대조군이 **내 정적 규칙의 진짜 버그도 잡아냈다**: `required: null`을 `is not None` 가드가 조용히 건너뛰고 있었다(수정 완료, `src/lint.py`). oracle을 안 돌렸으면 못 봤을 버그다.

**(c) 손검증 10개 (seed 777):** 무작위 10개 서버의 전 도구 스키마를 직접 읽고 판정 → **10/10 일치, 오판정률 0%.**

---

## 6. 기술적으로 가장 어려웠던 지점

1. **`npx` 좀비 프로세스 데드락 (실제로 첫 수집을 완전히 정지시킴).** `npx`가 손자 node 프로세스를 띄우는데, `npx`만 kill하면 손자가 stderr 파이프를 붙잡고 있어 `p.stderr.read()`가 **영원히 블록**된다. 400개 중 2개 처리하고 멈췄다. `start_new_session=True` + `os.killpg`로 프로세스 그룹 전체를 죽이고 stderr는 별도 스레드로 읽어 해결. 이후 성공률 2/12 → **85%**.
2. **서버 기동률.** 레지스트리 메타데이터에 선언되지 않은 env var를 요구하는 서버가 많았다. stderr에서 `[A-Z_]{5,}` 패턴을 긁어 더미값으로 1회 재시도하는 루프를 넣었다.
3. **`mcp` SDK v2가 `mcp.server.fastmcp`를 제거**해서 PyPI 서버 대부분이 import 단계에서 죽었다. `UV_CONSTRAINT`로 `mcp<2` 고정 → 성공률 0/8 → 4/8.
4. **Python 3.9밖에 없었다** (MCP SDK는 3.10+). `uv`를 설치해 3.12를 로컬 관리하도록 우회.
5. **가장 중요했던 판단:** "내가 짠 규칙으로 판정"을 버리고 **진짜 프로덕션 검증기 2개를 oracle로 돌린 것.** 직전 두 POC가 죽은 지점이 정확히 "내 판정을 믿었다"이므로, 여기서는 공식 SDK가 직접 판정하게 했다.

---

## 7. runtime 비용 구조

- **외부 usage-based API 호출: 없음.** LLM provider API 0회.
- 사용한 것: 무료 공개 MCP 레지스트리, npm/PyPI 공개 패키지, 공개 GitHub API(기존 `gh` 인증), 로컬 프로세스 실행.
- 판정 자체는 **순수 정적** — 스키마 620서버/14,000도구 판정에 수 초. LLM 불필요, 네트워크 불필요.
- 비용 구조상 이 도구는 $0로 무한히 돌릴 수 있다. **문제는 비용이 아니라 검출할 대상이 없다는 것.**

---

## 8. 데이터 출처 · 규모 · 한계 (자기 지적)

**출처:** `https://registry.modelcontextprotocol.io/v0/servers` (공식, 무료, 무인증) 전량 페이지네이션 → 최신 버전 6,100개 서버. 그중 npm/stdio 1,110 + PyPI/stdio ~690에서 seed 고정 무작위 추출 후 **로컬 기동 → 진짜 `tools/list` 응답 수집.**

**한계 — 정직하게:**
1. **가장 큰 구멍: Go/OCI 서버를 측정하지 못했다.** 이 환경에 docker가 없어 OCI 130개를 못 돌렸다. 그런데 후보가 인용한 **A-위반 실사례는 전부 Go 서버**(`github-mcp-server`, `docker/mcp-gateway`)다. 즉 **A=0.0%는 "손으로 스키마를 쓰는 생태계를 빼고 잰 값"일 수 있다.** 이걸 재려면 docker가 필요하다. — 다만 이 구멍이 메워져도 결론은 바뀌기 어렵다: OCI는 전체 모집단의 **2.1%**(130/6,100)이고, 설령 그 전부가 깨져 있어도 생태계 전체 비율은 2.1% 상한으로 **여전히 park 임계(5%) 미만**이다.
2. **기동 실패 서버 360개를 못 봤다.** 그중 81개는 자격증명 요구(AUTH_REQUIRED로만 기록), 279개는 기타 기동 실패. 이들이 체계적으로 더 깨져 있을 근거는 없지만 배제할 수도 없다.
3. **레지스트리 자체의 편향.** 자기 등록 방식이라 스팸이 많다. §5-1에서 dedup·별·다운로드·최근 커밋으로 잘라봤고 A는 전부 0.0%였다.
4. **npm이 과대표집**(502 vs PyPI 118). 다만 A=0%는 두 생태계 모두에서 동일.
5. **B의 판정 기준이 클라이언트 구현에 의존한다.** 현행 Agents SDK 기준으로는 서버가 안 죽는다. raw API에 `strict:true`로 도구를 통째로 넘기는 순진한 클라이언트에서는 400이 나겠지만, 그런 클라이언트를 실제로 확인하지는 못했다(호출 금지 정책상 검증 불가).

---

## 9. 소요 시간

약 3시간 (상한 준수). 대략: 수집 하네스 구축·디버깅 70분(좀비 프로세스 문제가 대부분), 사양 조사 30분, 수집 실행 50분(백그라운드 병행), oracle·자기공격·보고 30분.

---

## 10. 결론

**WORSE. park.**

- 사전 등록 지표 **0.0% (0/620)**, park 임계 5%의 한참 아래.
- npm·PyPI·holdout·활성 부분집합·퍼블리셔 dedup **전부 0.0%**. 깨질 구석이 없다.
- 양성 대조군 7/7 + 손검증 10/10으로 **검출기가 정상임을 증명한 뒤 나온 0%**다.
- 후보의 핵심 논리(스키마 1개 → 서버 전체 사망)는 **메커니즘은 실재하지만**(공식 SDK 소스로 확인) **모집단에 발현이 없다.** 상류(Agents SDK의 도구 단위 강등, SDK가 스키마를 생성하는 구조)가 이미 이 문제를 흡수했다.
- 유일하게 큰 숫자였던 B(27.6%)는 §4대로 **"3~5줄로 고칠 결함"이 아니라 strict mode의 표현력 한계**이고, 고칠 주체도 서버가 아니다.

**남은 단 하나의 재검토 트리거:** docker가 있는 환경에서 **Go로 작성된 OCI 배포 MCP 서버**만 따로 측정. 거기서 A가 유의미하게 나오면 "Go 생태계 한정 linter"라는 훨씬 좁은 후보로 재정의는 가능하다. 단 상한이 전체의 2.1%이므로 원래 가설의 부활은 아니다.
