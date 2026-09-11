/**
 * response-validator.mjs
 * ──────────────────────
 * 자비스 응답 출력 직전 단정 표현 검출 + 사후 LLM fact-check.
 *
 * 가드 #1 (즉효): regex 기반 단정 표현 검출 → 응답 보류 + 재작성 신호
 * 가드 #4 (정밀): LLM이 자기 응답을 다시 검증 → 거짓 발견 시 재생성 신호
 *
 * 사고 사례:
 *   2026-04-28 — 자비스가 "RAG 자동 인덱싱 → 자동 prepend / 하네스가 자동 차단" 단정.
 *   실측 결과 RAG 인덱싱 X (파일 직접 readFileSync), 하네스도 수동 호출 의존.
 *
 * 사용법:
 *   import { validateResponse, factCheckResponse } from './response-validator.mjs';
 *
 *   const validation = validateResponse(claudeOutputText);
 *   if (validation.severity === 'block') {
 *     // 응답 보류 + 재생성 요청
 *   }
 *
 *   const factCheck = await factCheckResponse(claudeOutputText, claudeClient, originalPrompt);
 *   if (!factCheck.passed) {
 *     // 거짓 발견 — 재생성
 *   }
 */

// ────────────────────────────────────────────────────────────
// 가드 #1 — 단정 표현 regex 검출 (즉효, LLM 호출 X, 5ms 이내)
// ────────────────────────────────────────────────────────────

/**
 * 단정 표현 패턴 — 3단계 위험도.
 * critical: 거의 무조건 거짓 신호 (실측 없는 100%/절대/항상)
 * warn:     조건부 거짓 가능성 (자동/모두/완전히)
 * info:     맥락 의존 (대체로/일반적으로)
 */
const ASSERTIVE_PATTERNS = {
  critical: [
    { regex: /100%\s*(?:확실|보장|차단|동작|안전|성공|정확|작동)/g, label: '100% 단언' },
    { regex: /절대\s*(?:안\s*함|되지\s*않|차단|보장)/g, label: '절대 단언' },
    { regex: /(?:다시는|결코)\s*(?:없|안\s*함|반복하지\s*않)/g, label: '미래 단언' },
    { regex: /(?:완전히|완벽하게)\s*(?:차단|방어|해결|동작|작동)/g, label: '완전성 단언' },
    { regex: /자동으로\s*(?:차단|방어|해결|prepend|발동)/g, label: '자동 동작 단언' },
    // 가드 #10 (2026-04-29): 거짓 단정 6건 패턴 학습 — 실측 회피 시 자주 등장하는 단언
    { regex: /(?:박힘|주입|노출|호출|매칭|발동|적용|작동|기록)\s*0건/g, label: '0건 단언 (실측 회피 위험)' },
    { regex: /(?:정확\s*동일|완전\s*동일|정확히\s*일치|정확\s*일치|완벽히\s*일치)/g, label: '동일성 단언 (실측 회피 위험)' },
    { regex: /이미\s*(?:박혀|적용되|등재되|주입되|작동되)\s*있/g, label: '자가 발견 단언 (실측 회피 위험)' },
    { regex: /(?:확정됨|확정\s*됨|확정입니다|확정됐)(?!\s*(?:만|다만|단|\?))/g, label: '확정 단언' },
  ],
  warn: [
    { regex: /항상\s*(?:동작|작동|올바|정확|성공)/g, label: '항상 동작 단언' },
    { regex: /(?:모든|전체)\s*(?:케이스|경우|상황)\s*(?:에서|을|를)\s*(?:차단|방어|해결)/g, label: '전체 차단 단언' },
    { regex: /확실히\s*(?:동작|차단|보장|방어)/g, label: '확실 단언' },
    { regex: /보장합니다(?!\s*(?:만|다만|단|\?))/g, label: '보장 단언' },
    // 가드 #10 (2026-04-29): 부정 단정 — "미주입·미적용·전혀 없" 등
    { regex: /(?:미주입|미적용|미발동|미실행|미작동)\s*(?:상태|확정)?/g, label: '부정 단언 (실측 회피 위험)' },
    { regex: /(?:전혀|완전히)\s*(?:없습|없다|안\s*되|불가능)/g, label: '전무 단언' },
    // 가드 #6 (2026-04-29): 시스템 룰 위반 — 테이블(`| |`) 사용 금지
    // 시스템 프롬프트 명시 룰 "테이블(`| |`) 금지" 매 응답 위반 사례 누적.
    // markdown table separator 행(`|---|`, `| :--- |`) 검출 = 진짜 표 시그널.
    // 본문 중간의 텍스트 `|`는 무시, 행 단위 separator만 잡음.
    { regex: /^\|[\s:|-]*-+[\s:|-]*\|$/gm, label: '시스템 룰 위반 — 테이블 사용 금지 (Discord 모바일 가독성 ↓)' },
  ],
  info: [
    { regex: /(?:일반적으로|대체로|보통은)\s*(?:동작|작동)/g, label: '일반론' },
    { regex: /이제(?:는)?\s*(?:차단|방어|해결)됩니다/g, label: '시점 단언' },
  ],
};

/**
 * 정직 표현 화이트리스트 — 단정 옆에 있으면 critical → warn으로 완화.
 */
const HONESTY_NEAR = [
  /추정/, /가능성/, /검증\s*필요/, /실측\s*전엔/,
  /흐릿/, /확인\s*못/, /미검증/, /가설/,
];

/**
 * 가드 #11 (2026-04-29) — 실측 증거 패턴
 * 응답 본문에 다음 중 하나라도 있으면 "실측 증거 동반" 으로 판정.
 * 단정 표현이 있는데 증거 0건이면 severity 한 단계 상향 (info → warn, warn → block).
 */
const EVIDENCE_PATTERNS = [
  /```[\w]*[\s\S]+?```/,              // 코드 블록 (실제 출력 인용)
  /실측\s*(?:결과|증거|값|확인)/,         // 명시적 실측 라벨
  /증거(?:\s*\d|\s*:|\s*-)/,          // "증거:" 또는 "증거 1"
  /grep\s+/,                            // shell 명령
  /awk\s+/,
  /(?:^|\s)\$\s*\w+/m,                // shell prompt
  /[A-Za-z_][A-Za-z0-9_/.-]+(?:\.js|\.mjs|\.ts|\.py|\.sh|\.json|\.md)#?L\d+/,  // 파일#L번호
  /(?:파일|file)\s*:\s*[\w./-]+/i,
  /(?:라인|line)\s*\d+/i,
  /로그\s*(?:인용|출력|확인)/,
  /(?:mtime|ctime|stat)/i,
];

/**
 * @param {string} text - 자비스 응답 본문
 * @returns {{
 *   severity: 'pass'|'info'|'warn'|'block',
 *   matches: Array<{level, label, snippet}>,
 *   honestyNearby: boolean,
 *   summary: string
 * }}
 */
export function validateResponse(text) {
  if (!text || typeof text !== 'string') {
    return { severity: 'pass', matches: [], honestyNearby: false, summary: 'empty' };
  }

  const matches = [];
  for (const [level, patterns] of Object.entries(ASSERTIVE_PATTERNS)) {
    for (const { regex, label } of patterns) {
      const found = [...text.matchAll(regex)];
      for (const m of found) {
        const start = Math.max(0, m.index - 30);
        const end = Math.min(text.length, m.index + m[0].length + 30);
        const snippet = text.slice(start, end).replace(/\n/g, ' ');
        matches.push({ level, label, snippet, raw: m[0] });
      }
    }
  }

  // 정직 표현이 같은 응답 내에 있으면 critical 강도 완화
  const honestyNearby = HONESTY_NEAR.some(rx => rx.test(text));

  // 등급 판정
  const counts = {
    critical: matches.filter(m => m.level === 'critical').length,
    warn: matches.filter(m => m.level === 'warn').length,
    info: matches.filter(m => m.level === 'info').length,
  };

  let severity = 'pass';
  if (counts.critical > 0) {
    // 정직 표현이 있으면 warn으로 완화, 없으면 block
    severity = honestyNearby ? 'warn' : 'block';
  } else if (counts.warn >= 2) {
    severity = 'warn';
  } else if (counts.warn === 1) {
    // 가드 #6: 표 룰 위반은 단독 1건만으로도 warn 강제 (다음 turn 정정 신호 보장)
    const hasTableViolation = matches.some(m => /테이블\s*사용\s*금지/.test(m.label));
    // 가드 #10 (2026-04-29): "실측 회피 위험" 라벨 + 부정/전무 단언도 단독 1건만으로 warn 강제
    const hasFalseAssertionRisk = matches.some(m => m.level === 'warn' &&
      (/실측\s*회피\s*위험/.test(m.label) || /부정\s*단언/.test(m.label) || /전무\s*단언/.test(m.label))
    );
    severity = (hasTableViolation || hasFalseAssertionRisk) ? 'warn' : 'info';
  } else if (counts.info >= 2) {
    severity = 'info';
  }

  // 가드 #11 (2026-04-29) — 실측 증거 부재 시 severity 상향
  // 단정/단언이 있는데 응답 본문에 코드 블록·grep 출력·라인 번호·로그 인용 등
  // 실측 증거가 0건이면 한 단계 더 강하게 신호 → 다음 turn 정정 prepend 강화.
  // 회귀 안전: 정직 표현(추정/가능성)으로 이미 완화된 경우는 적용 안 함 (false positive 차단).
  const hasEvidence = EVIDENCE_PATTERNS.some(rx => rx.test(text));
  if (!hasEvidence && !honestyNearby) {
    if (severity === 'warn' && counts.critical === 0) {
      // warn → block: 단정 1건 + 증거 0 + 정직 표현 0 = 강한 신호
      severity = 'block';
    } else if (severity === 'info' && counts.warn >= 1) {
      // info → warn: 약한 단정도 증거 부재 + 정직 부재면 다음 turn 신호 보장
      severity = 'warn';
    }
  }

  const summary = `critical=${counts.critical} warn=${counts.warn} info=${counts.info} honesty=${honestyNearby ? 'Y' : 'N'} → ${severity}`;
  return { severity, matches, honestyNearby, summary, counts };
}

/**
 * 응답 본문에 단정 경고 주석을 자동 부착 (block 시).
 * @param {string} text
 * @param {object} validation - validateResponse 결과
 * @returns {string} 보강된 응답
 */
export function annotateResponse(text, validation) {
  if (validation.severity === 'pass' || validation.severity === 'info') return text;

  const lines = [];
  if (validation.severity === 'block') {
    lines.push('⚠️  **자기검열 알림**: 응답에 단정 표현이 감지되었습니다. 재작성 권장:');
  } else {
    lines.push('💡 **자기검열 권고**: 단정 톤 완화 권장:');
  }
  for (const m of validation.matches.slice(0, 3)) {
    lines.push(`  - [${m.level}] ${m.label}: "${m.snippet.trim()}"`);
  }
  return text + '\n\n---\n' + lines.join('\n');
}

// ────────────────────────────────────────────────────────────
// 가드 #4 — LLM 사후 fact-check (정밀, LLM 호출, 30~60s)
// ────────────────────────────────────────────────────────────

/**
 * Claude 응답을 다시 Claude(또는 cheaper model)에 던져 단정 검증.
 *
 * @param {string} responseText - 자비스 응답 본문
 * @param {object} claudeClient - Anthropic SDK 클라이언트 (messages.create)
 * @param {string} originalPrompt - 사용자 원 질문 (맥락 제공)
 * @param {object} opts - { model='claude-haiku-4-5', maxRetries=1 }
 * @returns {Promise<{passed: boolean, issues: Array<string>, recommendation: string, raw?: string}>}
 */
export async function factCheckResponse(responseText, claudeClient, originalPrompt, opts = {}) {
  const { model = 'claude-haiku-4-5', maxRetries = 1 } = opts;

  if (!claudeClient || typeof claudeClient.messages?.create !== 'function') {
    return {
      passed: true,
      issues: [],
      recommendation: 'no-client',
      raw: 'claudeClient 미제공 — fact-check 스킵',
    };
  }

  const systemPrompt = `당신은 자비스 응답 fact-check 감사관입니다.
오답노트 5원칙(편향 제거):
1. 단일 가설 확정 금지 — "확정/원인이다" 단언 검증
2. 실측 선행 — 코드 추론만으로 결론 X
3. 독립 감사관 — 자기 진단의 자기 편향 의심
4. 미니멀 수정 유혹 경계 — "2줄만 고치면" 일수록 전제 구멍 큼
5. 권고→실행 자동 루프 금지

다음 자비스 응답을 검토해 단정 표현·근거 없는 단언·과장을 식별하세요.

응답을 JSON으로:
{
  "passed": <true if 단정 없음 or 모두 정직 표현 동반, false otherwise>,
  "issues": ["문제 표현 1", "문제 표현 2", ...],
  "recommendation": "재작성 방향 한 줄"
}`;

  const userMsg = `[사용자 원 질문]\n${originalPrompt || '(미제공)'}\n\n[자비스 응답]\n${responseText.slice(0, 4000)}`;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      const result = await claudeClient.messages.create({
        model,
        max_tokens: 600,
        system: systemPrompt,
        messages: [{ role: 'user', content: userMsg }],
      });
      const raw = result?.content?.[0]?.text || '';
      const jsonMatch = raw.match(/\{[\s\S]*\}/);
      if (!jsonMatch) {
        if (attempt === maxRetries) {
          return { passed: true, issues: [], recommendation: 'parse-failed', raw };
        }
        continue;
      }
      const parsed = JSON.parse(jsonMatch[0]);
      return {
        passed: !!parsed.passed,
        issues: Array.isArray(parsed.issues) ? parsed.issues : [],
        recommendation: parsed.recommendation || '',
        raw,
      };
    } catch (err) {
      if (attempt === maxRetries) {
        return {
          passed: true,
          issues: [],
          recommendation: `fact-check error: ${err.message}`,
          raw: '',
        };
      }
    }
  }
  return { passed: true, issues: [], recommendation: 'unreachable', raw: '' };
}

// ────────────────────────────────────────────────────────────
// 가드 #1 + #4 통합 — 응답 검증 파이프라인
// ────────────────────────────────────────────────────────────

/**
 * 응답을 (1) regex 검증 (2) 필요 시 LLM fact-check.
 * regex가 block이면 LLM fact-check 자동 발동.
 *
 * @param {string} responseText
 * @param {object} options - { claudeClient, originalPrompt, llmCheckOnBlock=true }
 * @returns {Promise<{
 *   regexValidation: object,
 *   llmFactCheck: object|null,
 *   finalVerdict: 'pass'|'warn'|'block',
 *   needsRewrite: boolean
 * }>}
 */
export async function validateAndFactCheck(responseText, options = {}) {
  const { claudeClient, originalPrompt, llmCheckOnBlock = true } = options;

  const regexValidation = validateResponse(responseText);

  let llmFactCheck = null;
  if (llmCheckOnBlock && regexValidation.severity === 'block' && claudeClient) {
    llmFactCheck = await factCheckResponse(responseText, claudeClient, originalPrompt);
  }

  let finalVerdict = regexValidation.severity;
  if (llmFactCheck && !llmFactCheck.passed) {
    finalVerdict = 'block';
  } else if (llmFactCheck && llmFactCheck.passed && finalVerdict === 'block') {
    // LLM fact-check 통과 = 정직 표현 동반 가능성 → warn으로 완화
    finalVerdict = 'warn';
  }

  return {
    regexValidation,
    llmFactCheck,
    finalVerdict,
    needsRewrite: finalVerdict === 'block',
  };
}

// ────────────────────────────────────────────────────────────
// CLI 진입점 (테스트 용도)
// ────────────────────────────────────────────────────────────
if (import.meta.url === `file://${process.argv[1]}`) {
  const sample = process.argv[2] || `이제 다시는 같은 거짓 답변 안 합니다. 하네스가 자동으로 차단합니다. 100% 보장됩니다.`;
  const result = validateResponse(sample);
  console.log('Input:', sample);
  console.log('Result:', JSON.stringify(result, null, 2));
  process.exit(result.severity === 'block' ? 1 : 0);
}
