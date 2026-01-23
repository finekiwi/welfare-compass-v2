"""
Retriever 정량 평가 스크립트 v2.1

준용 문서 기준 세부 지표 포함:
- FAQ: Hit@1, Hit@3, Hit@5, MRR@10
- Compare/Explore: Recall@k, nDCG@k
- 공통: UniquePolicy@k, DuplicateRate@k

사용법:
    python evaluate_retriever.py -f ../../data/test_dataset.json
    python evaluate_retriever.py -f ../../data/test_dataset.json --show-failed
    python evaluate_retriever.py -f ../../data/test_dataset.json -o results.json
    python evaluate_retriever.py -f ../../data/test_dataset.json --delay 6  # Rate limit 대응
"""

import sys
import os
import time
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'embeddings'))

import json
import argparse
import math
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict

from ensemble_retriever import ensemble_search


# ============================================================================
# 상수
# ============================================================================
K_VALUES = [1, 3, 5, 10, 20, 50]  # 평가할 k값들
DEFAULT_TOP_K = 50  # 리트리버에서 가져올 최대 개수


# ============================================================================
# 데이터 클래스
# ============================================================================
@dataclass
class CaseResult:
    """단일 테스트 케이스 평가 결과"""
    id: str
    intent: str
    difficulty: str
    category: str
    query: str
    ground_truth: List[str]
    retrieved: List[str]
    
    # FAQ 지표
    hit_at: Dict[int, int] = field(default_factory=dict)  # {1: 0/1, 3: 0/1, 5: 0/1}
    mrr_at_10: float = 0.0
    
    # Compare/Explore 지표
    recall_at: Dict[int, float] = field(default_factory=dict)
    ndcg_at: Dict[int, float] = field(default_factory=dict)
    
    # 다양성 지표
    unique_policy_at: Dict[int, float] = field(default_factory=dict)
    duplicate_rate_at: Dict[int, float] = field(default_factory=dict)
    
    # Compare 전용
    both_retrieved_at: Dict[int, int] = field(default_factory=dict)


@dataclass
class EvalSummary:
    """전체 평가 요약"""
    total: int = 0
    
    # FAQ 평균
    avg_hit_at: Dict[int, float] = field(default_factory=dict)
    avg_mrr_at_10: float = 0.0
    
    # Compare/Explore 평균
    avg_recall_at: Dict[int, float] = field(default_factory=dict)
    avg_ndcg_at: Dict[int, float] = field(default_factory=dict)
    
    # Compare 전용
    avg_both_retrieved_at: Dict[int, float] = field(default_factory=dict)
    
    # 다양성 평균
    avg_unique_policy_at: Dict[int, float] = field(default_factory=dict)
    avg_duplicate_rate_at: Dict[int, float] = field(default_factory=dict)
    
    # breakdown
    by_intent: Dict[str, Dict] = field(default_factory=dict)
    by_difficulty: Dict[str, Dict] = field(default_factory=dict)
    by_category: Dict[str, Dict] = field(default_factory=dict)
    
    # 실패 케이스
    failed_cases: List[CaseResult] = field(default_factory=list)


# ============================================================================
# 지표 계산 함수들
# ============================================================================
def calc_hit_at_k(ground_truth: List[str], retrieved: List[str], k: int) -> int:
    """Hit@k: 정답이 Top-k에 있으면 1, 없으면 0"""
    retrieved_k = set(retrieved[:k])
    gt_set = set(ground_truth)
    return 1 if gt_set & retrieved_k else 0


def calc_mrr_at_k(ground_truth: List[str], retrieved: List[str], k: int = 10) -> float:
    """MRR@k: 첫 정답의 순위 역수 (k 밖이면 0)"""
    gt_set = set(ground_truth)
    for i, doc_id in enumerate(retrieved[:k]):
        if doc_id in gt_set:
            return 1.0 / (i + 1)
    return 0.0


def calc_recall_at_k(ground_truth: List[str], retrieved: List[str], k: int) -> float:
    """Recall@k: 찾은 정답 수 / 전체 정답 수"""
    if not ground_truth:
        return 0.0
    retrieved_k = set(retrieved[:k])
    gt_set = set(ground_truth)
    found = len(gt_set & retrieved_k)
    return found / len(gt_set)


def calc_ndcg_at_k(ground_truth: List[str], retrieved: List[str], k: int) -> float:
    """nDCG@k: 랭킹 품질 (이진 관련도 사용)"""
    gt_set = set(ground_truth)
    
    # DCG 계산
    dcg = 0.0
    for i, doc_id in enumerate(retrieved[:k]):
        if doc_id in gt_set:
            # 이진 관련도: 정답이면 1, 아니면 0
            dcg += 1.0 / math.log2(i + 2)  # i+2 because log2(1) = 0
    
    # Ideal DCG 계산 (모든 정답이 상위에 있을 때)
    ideal_hits = min(len(gt_set), k)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(ideal_hits))
    
    return dcg / idcg if idcg > 0 else 0.0


def calc_unique_policy_at_k(retrieved: List[str], k: int) -> float:
    """UniquePolicy@k: Top-k 내 고유 정책 비율"""
    retrieved_k = retrieved[:k]
    if not retrieved_k:
        return 0.0
    unique_count = len(set(retrieved_k))
    return unique_count / len(retrieved_k)


def calc_duplicate_rate_at_k(retrieved: List[str], k: int) -> float:
    """DuplicateRate@k: 1 - UniquePolicy@k"""
    return 1.0 - calc_unique_policy_at_k(retrieved, k)


def calc_both_retrieved_at_k(ground_truth: List[str], retrieved: List[str], k: int) -> int:
    """both_retrieved@k: Compare용 - 두 정책 모두 Top-k에 있으면 1"""
    if len(ground_truth) != 2:
        return 0
    retrieved_k = set(retrieved[:k])
    return 1 if all(gt in retrieved_k for gt in ground_truth) else 0


# ============================================================================
# 평가 로직
# ============================================================================
def evaluate_single_case(
    case: Dict[str, Any],
    use_reranker: bool
) -> CaseResult:
    """단일 테스트 케이스 평가"""
    query = case["query"]
    ground_truth = case["ground_truth"]
    intent = case["intent"]
    
    # 검색 실행 (Top-50)
    results = ensemble_search(
        query=query,
        k=DEFAULT_TOP_K,
        use_reranker=use_reranker,
        include_expired=True,
        verbose=False
    )
    
    # plcyNo 추출
    retrieved = [doc.metadata.get("plcyNo", "") for doc in results]
    
    # 결과 객체 생성
    result = CaseResult(
        id=case["id"],
        intent=intent,
        difficulty=case["difficulty"],
        category=case["category"],
        query=query,
        ground_truth=ground_truth,
        retrieved=retrieved
    )
    
    # 지표 계산
    for k in K_VALUES:
        # 공통 지표
        result.unique_policy_at[k] = calc_unique_policy_at_k(retrieved, k)
        result.duplicate_rate_at[k] = calc_duplicate_rate_at_k(retrieved, k)
        
        if intent == "faq":
            # FAQ 지표
            result.hit_at[k] = calc_hit_at_k(ground_truth, retrieved, k)
            result.recall_at[k] = calc_recall_at_k(ground_truth, retrieved, k)
        elif intent == "compare":
            # Compare 지표
            result.both_retrieved_at[k] = calc_both_retrieved_at_k(ground_truth, retrieved, k)
            result.recall_at[k] = calc_recall_at_k(ground_truth, retrieved, k)
            result.ndcg_at[k] = calc_ndcg_at_k(ground_truth, retrieved, k)
        else:  # explore
            # Explore 지표
            result.recall_at[k] = calc_recall_at_k(ground_truth, retrieved, k)
            result.ndcg_at[k] = calc_ndcg_at_k(ground_truth, retrieved, k)
    
    # MRR@10 (FAQ용)
    if intent == "faq":
        result.mrr_at_10 = calc_mrr_at_k(ground_truth, retrieved, k=10)
    
    return result


def aggregate_results(results: List[CaseResult]) -> EvalSummary:
    """결과 집계"""
    summary = EvalSummary(total=len(results))
    
    # intent별 분리
    faq_results = [r for r in results if r.intent == "faq"]
    compare_results = [r for r in results if r.intent == "compare"]
    explore_results = [r for r in results if r.intent == "explore"]
    
    # FAQ 평균
    if faq_results:
        for k in K_VALUES:
            hits = [r.hit_at.get(k, 0) for r in faq_results]
            summary.avg_hit_at[k] = sum(hits) / len(hits)
        summary.avg_mrr_at_10 = sum(r.mrr_at_10 for r in faq_results) / len(faq_results)
    
    # Compare 평균
    if compare_results:
        for k in K_VALUES:
            both = [r.both_retrieved_at.get(k, 0) for r in compare_results]
            summary.avg_both_retrieved_at[k] = sum(both) / len(both)
            recalls = [r.recall_at.get(k, 0) for r in compare_results]
            ndcgs = [r.ndcg_at.get(k, 0) for r in compare_results]
            if k not in summary.avg_recall_at:
                summary.avg_recall_at[k] = 0
            if k not in summary.avg_ndcg_at:
                summary.avg_ndcg_at[k] = 0
    
    # Explore + Compare Recall/nDCG 평균
    recall_explore = compare_results + explore_results
    if recall_explore:
        for k in K_VALUES:
            recalls = [r.recall_at.get(k, 0) for r in recall_explore]
            summary.avg_recall_at[k] = sum(recalls) / len(recalls)
            ndcgs = [r.ndcg_at.get(k, 0) for r in recall_explore]
            summary.avg_ndcg_at[k] = sum(ndcgs) / len(ndcgs)
    
    # 다양성 평균 (전체)
    for k in K_VALUES:
        uniques = [r.unique_policy_at.get(k, 0) for r in results]
        summary.avg_unique_policy_at[k] = sum(uniques) / len(uniques)
        dups = [r.duplicate_rate_at.get(k, 0) for r in results]
        summary.avg_duplicate_rate_at[k] = sum(dups) / len(dups)
    
    # Breakdown by intent
    for intent, intent_results in [("faq", faq_results), ("compare", compare_results), ("explore", explore_results)]:
        if not intent_results:
            continue
        summary.by_intent[intent] = {
            "total": len(intent_results),
        }
        if intent == "faq":
            summary.by_intent[intent]["hit_at_1"] = sum(r.hit_at.get(1, 0) for r in intent_results) / len(intent_results)
            summary.by_intent[intent]["hit_at_3"] = sum(r.hit_at.get(3, 0) for r in intent_results) / len(intent_results)
            summary.by_intent[intent]["hit_at_5"] = sum(r.hit_at.get(5, 0) for r in intent_results) / len(intent_results)
            summary.by_intent[intent]["mrr_at_10"] = sum(r.mrr_at_10 for r in intent_results) / len(intent_results)
        elif intent == "compare":
            summary.by_intent[intent]["both_retrieved_at_10"] = sum(r.both_retrieved_at.get(10, 0) for r in intent_results) / len(intent_results)
            summary.by_intent[intent]["recall_at_10"] = sum(r.recall_at.get(10, 0) for r in intent_results) / len(intent_results)
        else:  # explore
            summary.by_intent[intent]["recall_at_50"] = sum(r.recall_at.get(50, 0) for r in intent_results) / len(intent_results)
            summary.by_intent[intent]["duplicate_rate_at_10"] = sum(r.duplicate_rate_at.get(10, 0) for r in intent_results) / len(intent_results)
    
    # Breakdown by difficulty
    for diff in ["easy", "medium", "hard"]:
        diff_results = [r for r in results if r.difficulty == diff]
        if not diff_results:
            continue
        faq_diff = [r for r in diff_results if r.intent == "faq"]
        summary.by_difficulty[diff] = {
            "total": len(diff_results),
            "hit_at_5": sum(r.hit_at.get(5, 0) for r in faq_diff) / len(faq_diff) if faq_diff else 0,
        }
    
    # Breakdown by category
    for cat in ["일자리", "주거", "교육", "복지문화", "참여권리"]:
        cat_results = [r for r in results if r.category == cat]
        if not cat_results:
            continue
        faq_cat = [r for r in cat_results if r.intent == "faq"]
        summary.by_category[cat] = {
            "total": len(cat_results),
            "hit_at_5": sum(r.hit_at.get(5, 0) for r in faq_cat) / len(faq_cat) if faq_cat else 0,
        }
    
    # 실패 케이스 (Hit@5 실패한 FAQ)
    summary.failed_cases = [r for r in faq_results if r.hit_at.get(5, 0) == 0]
    
    return summary


def evaluate_retriever(
    test_cases: List[Dict],
    use_reranker: bool,
    verbose: bool = False,
    rate_limit_delay: float = 0
) -> EvalSummary:
    """전체 테스트셋 평가
    
    Args:
        test_cases: 테스트 케이스 리스트
        use_reranker: 리랭커 사용 여부
        verbose: 진행률 출력 여부
        rate_limit_delay: 리랭커 호출 간 대기 시간(초). Cohere Trial은 6 권장
    """
    results = []
    
    for i, case in enumerate(test_cases):
        if verbose:
            print(f"\r평가 중... {i+1}/{len(test_cases)}", end="", flush=True)
        result = evaluate_single_case(case, use_reranker)
        results.append(result)
        
        # Rate limit 대응 (리랭커 사용 시에만)
        if use_reranker and rate_limit_delay > 0:
            time.sleep(rate_limit_delay)
    
    if verbose:
        print()
    
    return aggregate_results(results)


# ============================================================================
# A/B 테스트
# ============================================================================
def run_ab_test(
    test_cases: List[Dict],
    verbose: bool = True,
    rate_limit_delay: float = 0
) -> Dict[str, EvalSummary]:
    """앙상블 vs 앙상블+리랭커 A/B 테스트
    
    Args:
        test_cases: 테스트 케이스 리스트
        verbose: 진행률 출력 여부
        rate_limit_delay: 리랭커 호출 간 대기 시간(초)
    """
    print(f"\n{'='*60}")
    print(f"A/B 테스트 시작")
    print(f"테스트 케이스: {len(test_cases)}개")
    if rate_limit_delay > 0:
        print(f"Rate limit delay: {rate_limit_delay}초")
        estimated_time = len(test_cases) * rate_limit_delay / 60
        print(f"예상 소요시간 (리랭커): ~{estimated_time:.1f}분")
    print('='*60)
    
    print("\n[A] 앙상블만 (리랭커 OFF)")
    result_a = evaluate_retriever(test_cases, use_reranker=False, verbose=verbose)
    
    print("\n[B] 앙상블 + 리랭커")
    result_b = evaluate_retriever(
        test_cases, 
        use_reranker=True, 
        verbose=verbose, 
        rate_limit_delay=rate_limit_delay
    )
    
    return {
        "ensemble_only": result_a,
        "ensemble_rerank": result_b
    }


def print_comparison(results: Dict[str, EvalSummary]):
    """A/B 결과 비교 출력"""
    a = results["ensemble_only"]
    b = results["ensemble_rerank"]
    
    print(f"\n{'='*60}")
    print(f"📊 A/B 테스트 결과")
    print('='*60)
    
    # 목표 대비 (준용 문서 기준)
    print(f"\n[목표 대비 달성률]")
    print(f"  {'지표':<25} {'앙상블만':>10} {'+ 리랭커':>10} {'목표':>10}")
    print(f"  {'-'*55}")
    
    # FAQ Hit@1 (목표 ≥ 0.80)
    hit1_a = a.avg_hit_at.get(1, 0)
    hit1_b = b.avg_hit_at.get(1, 0)
    print(f"  {'FAQ Hit@1':<25} {hit1_a:>9.1%} {hit1_b:>10.1%} {'>= 80%':>10}")
    
    # FAQ Hit@3 (목표 ≥ 0.95)
    hit3_a = a.avg_hit_at.get(3, 0)
    hit3_b = b.avg_hit_at.get(3, 0)
    print(f"  {'FAQ Hit@3':<25} {hit3_a:>9.1%} {hit3_b:>10.1%} {'>= 95%':>10}")
    
    # FAQ Hit@5
    hit5_a = a.avg_hit_at.get(5, 0)
    hit5_b = b.avg_hit_at.get(5, 0)
    print(f"  {'FAQ Hit@5':<25} {hit5_a:>9.1%} {hit5_b:>10.1%} {'-':>10}")
    
    # FAQ MRR@10
    mrr_a = a.avg_mrr_at_10
    mrr_b = b.avg_mrr_at_10
    print(f"  {'FAQ MRR@10':<25} {mrr_a:>9.3f} {mrr_b:>10.3f} {'-':>10}")
    
    # Compare both_retrieved@10 (목표 ≥ 0.90)
    both10_a = a.avg_both_retrieved_at.get(10, 0)
    both10_b = b.avg_both_retrieved_at.get(10, 0)
    print(f"  {'Compare both@10':<25} {both10_a:>9.1%} {both10_b:>10.1%} {'>= 90%':>10}")
    
    # Explore Recall@50 (목표 ≥ 0.90)
    recall50_a = a.avg_recall_at.get(50, 0)
    recall50_b = b.avg_recall_at.get(50, 0)
    print(f"  {'Explore Recall@50':<25} {recall50_a:>9.1%} {recall50_b:>10.1%} {'>= 90%':>10}")
    
    # DuplicateRate@10 (목표 < 0.20)
    dup10_a = a.avg_duplicate_rate_at.get(10, 0)
    dup10_b = b.avg_duplicate_rate_at.get(10, 0)
    print(f"  {'DuplicateRate@10':<25} {dup10_a:>9.1%} {dup10_b:>10.1%} {'< 20%':>10}")
    
    # Intent별
    print(f"\n[Intent별 상세]")
    for intent in ["faq", "compare", "explore"]:
        if intent not in a.by_intent and intent not in b.by_intent:
            continue
        print(f"\n  [{intent.upper()}]")
        
        a_data = a.by_intent.get(intent, {})
        b_data = b.by_intent.get(intent, {})
        
        if intent == "faq":
            print(f"    Hit@1:   {a_data.get('hit_at_1', 0):>6.1%}  →  {b_data.get('hit_at_1', 0):>6.1%}")
            print(f"    Hit@3:   {a_data.get('hit_at_3', 0):>6.1%}  →  {b_data.get('hit_at_3', 0):>6.1%}")
            print(f"    Hit@5:   {a_data.get('hit_at_5', 0):>6.1%}  →  {b_data.get('hit_at_5', 0):>6.1%}")
            print(f"    MRR@10:  {a_data.get('mrr_at_10', 0):>6.3f}  →  {b_data.get('mrr_at_10', 0):>6.3f}")
        elif intent == "compare":
            print(f"    both@10: {a_data.get('both_retrieved_at_10', 0):>6.1%}  →  {b_data.get('both_retrieved_at_10', 0):>6.1%}")
            print(f"    Recall@10: {a_data.get('recall_at_10', 0):>6.1%}  →  {b_data.get('recall_at_10', 0):>6.1%}")
        else:  # explore
            print(f"    Recall@50: {a_data.get('recall_at_50', 0):>6.1%}  →  {b_data.get('recall_at_50', 0):>6.1%}")
            print(f"    DupRate@10: {a_data.get('duplicate_rate_at_10', 0):>6.1%}  →  {b_data.get('duplicate_rate_at_10', 0):>6.1%}")
    
    # 난이도별
    print(f"\n[난이도별 Hit@5 (FAQ)]")
    print(f"  {'난이도':<10} {'앙상블만':>10} {'+ 리랭커':>10}")
    print(f"  {'-'*32}")
    for diff in ["easy", "medium", "hard"]:
        a_hit = a.by_difficulty.get(diff, {}).get("hit_at_5", 0)
        b_hit = b.by_difficulty.get(diff, {}).get("hit_at_5", 0)
        print(f"  {diff:<10} {a_hit:>9.1%} {b_hit:>10.1%}")
    
    # 승자 판정
    print(f"\n[결론]")
    wins_a = 0
    wins_b = 0
    if hit1_a > hit1_b: wins_a += 1
    elif hit1_b > hit1_a: wins_b += 1
    if hit5_a > hit5_b: wins_a += 1
    elif hit5_b > hit5_a: wins_b += 1
    if mrr_a > mrr_b: wins_a += 1
    elif mrr_b > mrr_a: wins_b += 1
    
    if wins_b > wins_a:
        print(f"  🏆 리랭커 추가 시 성능 향상")
    elif wins_a > wins_b:
        print(f"  🏆 앙상블만으로 충분")
    else:
        print(f"  🤝 큰 차이 없음")
    
    print()


def print_failed_cases(summary: EvalSummary, label: str, max_show: int = 10):
    """실패 케이스 출력"""
    if not summary.failed_cases:
        print(f"\n[{label}] 실패 케이스 없음 🎉")
        return
    
    print(f"\n[{label}] 실패 케이스 - Hit@5 미달 ({len(summary.failed_cases)}개)")
    print("-" * 60)
    
    for i, case in enumerate(summary.failed_cases[:max_show]):
        print(f"\n  {i+1}. [{case.id}] {case.difficulty}")
        print(f"     쿼리: {case.query}")
        print(f"     정답: {case.ground_truth}")
        print(f"     검색: {case.retrieved[:5]}")
    
    if len(summary.failed_cases) > max_show:
        print(f"\n  ... 외 {len(summary.failed_cases) - max_show}개")


# ============================================================================
# 메인
# ============================================================================
def load_test_cases(filepath: str) -> List[Dict]:
    """테스트 데이터셋 로드"""
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get("test_cases", [])


def main():
    parser = argparse.ArgumentParser(description="Retriever A/B 테스트 (세부 지표)")
    parser.add_argument(
        "--test-file", "-f",
        type=str,
        required=True,
        help="테스트 데이터셋 JSON 파일 경로"
    )
    parser.add_argument(
        "--show-failed",
        action="store_true",
        help="실패 케이스 출력"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="결과 JSON 저장 경로"
    )
    parser.add_argument(
        "--delay", "-d",
        type=float,
        default=0,
        help="리랭커 호출 간 대기 시간(초). Cohere Trial 키는 --delay 6 권장"
    )
    
    args = parser.parse_args()
    
    # 데이터 로드
    print(f"테스트 데이터 로드: {args.test_file}")
    test_cases = load_test_cases(args.test_file)
    print(f"로드 완료: {len(test_cases)}개 케이스")
    
    # A/B 테스트 실행
    results = run_ab_test(test_cases, rate_limit_delay=args.delay)
    
    # 결과 출력
    print_comparison(results)
    
    # 실패 케이스 출력
    if args.show_failed:
        print_failed_cases(results["ensemble_only"], "앙상블만")
        print_failed_cases(results["ensemble_rerank"], "앙상블+리랭커")
    
    # 결과 저장
    if args.output:
        output_data = {
            "test_file": args.test_file,
            "total_cases": len(test_cases),
            "ensemble_only": {
                "hit_at": results["ensemble_only"].avg_hit_at,
                "mrr_at_10": results["ensemble_only"].avg_mrr_at_10,
                "recall_at": results["ensemble_only"].avg_recall_at,
                "both_retrieved_at": results["ensemble_only"].avg_both_retrieved_at,
                "duplicate_rate_at": results["ensemble_only"].avg_duplicate_rate_at,
                "by_intent": results["ensemble_only"].by_intent,
                "by_difficulty": results["ensemble_only"].by_difficulty,
            },
            "ensemble_rerank": {
                "hit_at": results["ensemble_rerank"].avg_hit_at,
                "mrr_at_10": results["ensemble_rerank"].avg_mrr_at_10,
                "recall_at": results["ensemble_rerank"].avg_recall_at,
                "both_retrieved_at": results["ensemble_rerank"].avg_both_retrieved_at,
                "duplicate_rate_at": results["ensemble_rerank"].avg_duplicate_rate_at,
                "by_intent": results["ensemble_rerank"].by_intent,
                "by_difficulty": results["ensemble_rerank"].by_difficulty,
            }
        }
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        print(f"\n결과 저장됨: {args.output}")


if __name__ == "__main__":
    main()