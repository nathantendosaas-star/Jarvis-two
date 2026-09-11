// ssot-coverage-gate.mjs
// 면접 답변 파이프라인 하네스 — L1 SSoT Coverage Gate.
//
// 역할: 질문 + answerGuide + userProfile 3-소스를 합성해 "이 질문이 SSoT 커버리지 안인가" 판정.
// outOfScope=true면 fast-path가 STAR 매핑 강제를 비활성화하고 answerGuide 우선 모드로 전환.
//
// 2026-04-28 신설 — 시스템 결함 "v92-Q079 AI 입력 형식 변환 → STAR-3 IoT 어댑터 매핑(Frankenstein)"의
// 원천 차단 가드. 단일 user-profile.md만 보던 기존 fast-path의 단편 SSoT 한계를 메움.

// ─────────────────────────────────────────────────────────────
// SSoT 외 도메인 키워드 — user-profile.md 미등재 영역
// 질문 또는 answerGuide에 이 패턴 1개라도 등장 + user-profile 매칭 ≤ 1개면 outOfScope.
// ─────────────────────────────────────────────────────────────
export const SSOT_EXTERNAL_DOMAIN_PATTERNS = [
  // AI/ML 영역 (주인님 SSoT 부재 — 2026-04-28 v92-Q079 사고 트리거)
  /ML\s*팀|ML팀|머신러닝\s*팀|AI\s*팀|데이터\s*사이언스\s*팀|MLOps/i,
  /AI\s*모델\s*입력|모델\s*훈련|모델\s*학습|모델\s*튜닝|fine[-\s]*tuning|continued\s*pre[-\s]*training/i,
  /피처\s*엔지니어링|feature\s*engineering|임베딩\s*엔지니어링|벡터\s*임베딩\s*생성/i,
  /ProtoBuf\s*스키마|Avro\s*스키마|schema\s*registry/i,
  // 데이터 파이프라인 영역
  /Spark|Hadoop|Hive|Flink|Beam|Storm|Kinesis\s*Firehose/i,
  /Airflow|Prefect|Dagster|Argo\s*Workflow/i,
  /Snowflake|Databricks|BigQuery|Redshift|Athena/i,
  // 인프라 영역 (사이드 학습 단계)
  /Kubernetes|k8s|Helm|Istio|Service\s*Mesh|EKS|GKE/i,
  /Terraform|Ansible|Pulumi|CloudFormation/i,
  // 프론트/모바일
  /\bReact\b|Vue\.js|\bAngular\b|Flutter|React\s*Native|iOS\s*개발|Android\s*개발/i,
];

// ─────────────────────────────────────────────────────────────
// 토큰화 — 한글 명사구 + 영문 단어 추출
// ─────────────────────────────────────────────────────────────
function tokenize(text) {
  if (!text) return [];
  const lower = String(text).toLowerCase();
  // 영문 단어 + 한글 2자 이상 묶음 + 숫자 단위
  const tokens = lower.match(/[a-z][a-z0-9_-]{1,}|[가-힣]{2,}/g) || [];
  return [...new Set(tokens)];
}

// ─────────────────────────────────────────────────────────────
// userProfile 토큰 캐시 — 매 호출마다 토크나이즈 회피
// ─────────────────────────────────────────────────────────────
let _profileTokenCache = null;
let _profileSourceLength = 0;

function getProfileTokenSet(userProfile) {
  if (!userProfile) return new Set();
  if (_profileTokenCache && userProfile.length === _profileSourceLength) {
    return _profileTokenCache;
  }
  _profileTokenCache = new Set(tokenize(userProfile));
  _profileSourceLength = userProfile.length;
  return _profileTokenCache;
}

// ─────────────────────────────────────────────────────────────
// 핵심 API — 커버리지 평가
// ─────────────────────────────────────────────────────────────
/**
 * @param {Object} args
 * @param {string} args.question — 면접 질문 텍스트
 * @param {string} args.userProfile — user-profile.md 본문
 * @param {Object|null} args.scenarioMetadata — { answerGuide, slide, ... } 또는 null
 * @returns {{
 *   isOutOfScope: boolean,
 *   externalDomainHit: string|null,
 *   profileMatchCount: number,
 *   matchedTokens: string[],
 *   reasons: string[]
 * }}
 */
export function evaluateCoverage({ question, userProfile, scenarioMetadata = null }) {
  const reasons = [];
  const qText = String(question || '');
  const guideText = scenarioMetadata?.answerGuide ? String(scenarioMetadata.answerGuide) : '';
  const combined = `${qText}\n${guideText}`;

  // 1. 외부 도메인 패턴 검출 (질문 + answerGuide 합쳐서)
  const externalHit = SSOT_EXTERNAL_DOMAIN_PATTERNS.find(re => re.test(combined));

  // 2. user-profile 토큰 매칭 (질문에 한해)
  const profileTokens = getProfileTokenSet(userProfile);
  const qTokens = tokenize(qText);
  const matchedTokens = qTokens.filter(t => profileTokens.has(t) && t.length >= 3);

  // 3. 판정
  let isOutOfScope = false;
  if (externalHit && matchedTokens.length <= 1) {
    isOutOfScope = true;
    reasons.push(`SSoT 외 도메인 패턴 검출: ${externalHit.source.slice(0, 40)}`);
    reasons.push(`user-profile 매칭 토큰 ${matchedTokens.length}건 (≤1)`);
  } else if (externalHit) {
    reasons.push(`외부 도메인 등장하나 profile 매칭 ${matchedTokens.length}건 충분 — scope 안 (보조 모드)`);
  }

  return {
    isOutOfScope,
    externalDomainHit: externalHit ? externalHit.source : null,
    profileMatchCount: matchedTokens.length,
    matchedTokens: matchedTokens.slice(0, 10),
    reasons,
  };
}

// ─────────────────────────────────────────────────────────────
// L4 Pre-Send Gate — 메타 verifier 결과 기반 송출 결정
// fast-path가 verifyAnswerWithClaude 후 호출. creative.length + isOutOfScope 조합 임계.
// ─────────────────────────────────────────────────────────────
const PRESEND_CREATIVE_HARD_LIMIT = 5;         // 6건 사고(2026-04-28) 임계 — 5건 이상이면 무조건 차단
const PRESEND_CREATIVE_HARD_LIMIT_SCENARIO = 12; // v4.58: 시나리오(answerGuide 기반) 완화 임계
// 이유: 시나리오 질문은 PDF/슬라이드 내용이 정답 — Claude verifier가 user-profile에 없다고 "창작"으로
//       분류해도 실제로는 합법적 콘텐츠. 5건 임계는 과민 → 정상 PDF 기반 답변 차단 false positive.
const PRESEND_CREATIVE_OOS_LIMIT = 3;          // outOfScope일 땐 3건만 넘어도 차단 (더 엄격)

/**
 * @param {Object} args
 * @param {Array} args.creative — verifier 적발 creative array
 * @param {boolean} args.isOutOfScope — Coverage Gate 결과
 * @param {number} args.bodyLength — 답변 본문 길이 (너무 짧으면 차단 무의미)
 * @param {boolean} args.isScenario — answerGuide 기반 시나리오 질문 여부 (v4.58)
 * @returns {{ decision: 'PASS'|'BLOCK', reason: string, creativeCount: number }}
 */
export function evaluatePreSendGate({ creative = [], isOutOfScope = false, bodyLength = 0, isScenario = false }) {
  const creativeCount = Array.isArray(creative) ? creative.length : 0;
  if (bodyLength < 100) {
    return { decision: 'PASS', reason: 'body too short for meaningful gate', creativeCount };
  }
  // v4.58: 시나리오 모드는 완화된 임계 적용
  const hardLimit = isScenario ? PRESEND_CREATIVE_HARD_LIMIT_SCENARIO : PRESEND_CREATIVE_HARD_LIMIT;
  if (creativeCount >= hardLimit) {
    return {
      decision: 'BLOCK',
      reason: `creative ${creativeCount}건 ≥ HARD_LIMIT(${hardLimit})${isScenario ? '[scenario]' : ''}`,
      creativeCount,
    };
  }
  if (isOutOfScope && creativeCount >= PRESEND_CREATIVE_OOS_LIMIT) {
    return {
      decision: 'BLOCK',
      reason: `outOfScope + creative ${creativeCount}건 ≥ OOS_LIMIT(${PRESEND_CREATIVE_OOS_LIMIT})`,
      creativeCount,
    };
  }
  return { decision: 'PASS', reason: '', creativeCount };
}

// ─────────────────────────────────────────────────────────────
// 폴백 답변 빌더 — BLOCK 시 SSoT(answerGuide) 기반 1인칭 재구성
// v4.59 (2026-04-29 주인님 지시): "정직 답변 대체" 어조 제거. 경험 기반 답변 강제.
// answerGuide가 있으면 그것을 자기 경험 톤으로 직접 답변. 진짜 outOfScope일 때만 정직.
// LLM 호출 없는 결정적 텍스트.
// ─────────────────────────────────────────────────────────────
export function buildOutOfScopeFallback({ question, scenarioMetadata = null, externalDomainHit = null }) {
  const slide = scenarioMetadata?.slide ? `슬라이드 ${scenarioMetadata.slide}` : '발표 자료';
  const guide = scenarioMetadata?.answerGuide ? String(scenarioMetadata.answerGuide).slice(0, 600) : '';
  const domainHint = externalDomainHit ? ` (감지된 영역: ${externalDomainHit.slice(0, 40)})` : '';

  if (guide) {
    return [
      `${slide}에 정리한 내용으로 답변드립니다.`,
      '',
      guide,
      '',
      '이 부분이 제가 직접 검토하고 정리한 사실 기반 내용입니다. 추가로 디깅하실 영역이 있으시면 말씀해 주십시오.',
    ].join('\n');
  }

  return [
    `이 질문은 제 직접 경험 영역 밖이라 솔직히 말씀드리겠습니다${domainHint}.`,
    '',
    `${slide} 범위를 벗어나는 부분이라, 추측보다는 모른다고 인정하는 것이 정확합니다. 관련 영역에서 의사결정 원칙은 설명드릴 수 있으니 필요하시면 말씀해 주십시오.`,
  ].join('\n');
}
