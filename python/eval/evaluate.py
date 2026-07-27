"""
RAG 系统自动化评估。

指标体系：
- Context Precision: 检索到的上下文中有多少与标准答案相关
- Context Recall: 标准答案需要的信息有多少被检索到
- Faithfulness: 生成答案是否忠实于检索到的上下文
- Answer Relevancy: 生成答案与问题的相关度

用法: python -m eval.evaluate [--test-file test_cases.json] [--output report.json]
"""

import json
import asyncio
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# ── 内置测试用例（50 条） ────────────────────────────────

DEFAULT_TEST_CASES = [
    # === 规章制度类 (policy) ===
    {
        "question": "年假有多少天？",
        "ground_truth": "正式员工每年享有5天带薪年假，工龄每增加5年增加1天，上限15天。",
        "reference_docs": [],
        "category": "policy",
    },
    {
        "question": "病假需要什么证明材料？",
        "ground_truth": "病假3天以上需提供二级甲等以上医院出具的病假证明，3天以内可凭社区医院证明。",
        "reference_docs": [],
        "category": "policy",
    },
    {
        "question": "出差报销的流程是什么？",
        "ground_truth": "出差前填写出差申请单→部门审批→出差→回司后3个工作日内提交报销单→附票据→财务审核→打款。",
        "reference_docs": [],
        "category": "policy",
    },
    {
        "question": "加班工资怎么计算？",
        "ground_truth": "工作日加班1.5倍工资，休息日加班2倍工资，法定节假日加班3倍工资。",
        "reference_docs": [],
        "category": "policy",
    },
    {
        "question": "员工转正需要什么条件？",
        "ground_truth": "试用期3-6个月，工作表现合格，通过转正答辩，部门负责人审批。",
        "reference_docs": [],
        "category": "policy",
    },
    {
        "question": "公司有哪些福利？",
        "ground_truth": "五险一金、补充商业保险、年度体检、节日福利、带薪年假、餐补、交通补贴。",
        "reference_docs": [],
        "category": "policy",
    },
    {
        "question": "婚假有多少天？需要什么证明？",
        "ground_truth": "法定婚假3天，晚婚（男25女23以上）增加7天，需提供结婚证。",
        "reference_docs": [],
        "category": "policy",
    },
    {
        "question": "迟到的处罚规定是什么？",
        "ground_truth": "月累计迟到3次以内口头警告，3-5次书面警告，5次以上记过并影响当月绩效。",
        "reference_docs": [],
        "category": "policy",
    },
    {
        "question": "离职流程是怎样的？",
        "ground_truth": "提前30天书面申请→部门审批→HR面谈→办理交接→结算工资→办理离职证明。",
        "reference_docs": [],
        "category": "policy",
    },
    {
        "question": "社保和公积金的缴纳比例是多少？",
        "ground_truth": "社保单位16%个人8%，医保单位8%个人2%，公积金单位和个人各5-12%。",
        "reference_docs": [],
        "category": "policy",
    },
    {
        "question": "员工可以申请居家办公吗？",
        "ground_truth": "每周可申请不超过2天居家办公，需提前1天在OA系统提交申请并经直属上级批准。",
        "reference_docs": [],
        "category": "policy",
    },
    {
        "question": "培训费用的报销标准是什么？",
        "ground_truth": "岗位相关培训每年限额5000元，需签订培训协议，未满服务期离职需按比例退还。",
        "reference_docs": [],
        "category": "policy",
    },
    {
        "question": "产假和陪产假政策是什么？",
        "ground_truth": "女职工产假98天+30天奖励假，男职工陪产假15天。",
        "reference_docs": [],
        "category": "policy",
    },
    {
        "question": "绩效考核的周期和等级是怎样的？",
        "ground_truth": "季度考核+年度考核，等级分S/A/B/C/D五档，S档比例不超10%。",
        "reference_docs": [],
        "category": "policy",
    },
    {
        "question": "公司对员工兼职工有什么规定？",
        "ground_truth": "员工不得从事与公司业务存在竞争关系的兼职，其他兼职需向HR报备。",
        "reference_docs": [],
        "category": "policy",
    },
    # === 技术文档类 (tech_doc) ===
    {
        "question": "用户登录接口的参数有哪些？",
        "ground_truth": "POST /api/auth/login，参数：username(用户名)、password(密码)，返回JWT token和用户信息。",
        "reference_docs": [],
        "category": "tech_doc",
    },
    {
        "question": "系统部署需要哪些环境依赖？",
        "ground_truth": "JDK 21、Maven 3.9+、Node.js 20+、Python 3.12+、Docker、MySQL 8.0、MinIO、Qdrant。",
        "reference_docs": [],
        "category": "tech_doc",
    },
    {
        "question": "数据库连接池的配置参数是什么？",
        "ground_truth": "HikariCP连接池：最大连接数20，最小空闲5，连接超时30秒，空闲超时10分钟，最大生命周期30分钟。",
        "reference_docs": [],
        "category": "tech_doc",
    },
    {
        "question": "如果Qdrant服务不可用，系统如何处理？",
        "ground_truth": "系统自动降级：Agent→RAG模式→search-only→兜底回复。Qdrant无法连接时返回空结果并记录告警日志。",
        "reference_docs": [],
        "category": "tech_doc",
    },
    {
        "question": "文件上传支持哪些格式？大小限制是多少？",
        "ground_truth": "支持PDF、Markdown、TXT、DOCX格式，单个文件不超过20MB。上传后存储在MinIO对象存储。",
        "reference_docs": [],
        "category": "tech_doc",
    },
    {
        "question": "系统的缓存策略是什么？",
        "ground_truth": "当前MVP版本无专用缓存层，Qdrant向量检索结果在RAG模式下直接使用，Agent模式下通过ReAct循环复用工具调用结果。",
        "reference_docs": [],
        "category": "tech_doc",
    },
    {
        "question": "API接口的认证方式是什么？",
        "ground_truth": "Java对外接口使用JWT Bearer Token认证，Java→Python内部调用使用X-API-Key认证。",
        "reference_docs": [],
        "category": "tech_doc",
    },
    {
        "question": "如何使用Docker部署系统？",
        "ground_truth": "在docker目录执行 docker compose up -d 启动全部服务（MySQL+Qdrant+MinIO+Python+Java+Nginx），或仅启动基础服务。",
        "reference_docs": [],
        "category": "tech_doc",
    },
    {
        "question": "文档索引的流程是怎样的？",
        "ground_truth": "用户上传文件→Java保存到MinIO→调用Python索引API→Python下载→分块→BGE-M3向量化(1024-dim)→存入Qdrant→同步BM25索引。",
        "reference_docs": [],
        "category": "tech_doc",
    },
    {
        "question": "系统的日志级别如何配置？",
        "ground_truth": "Java使用logback.xml配置，Python使用logging模块，默认级别INFO，调试时可设为DEBUG。",
        "reference_docs": [],
        "category": "tech_doc",
    },
    {
        "question": "SSE事件流的数据格式是什么？",
        "ground_truth": "data: {\"type\":\"answer\",\"content\":\"...\"}\\n\\n，支持9种事件类型，仅data行无event前缀。",
        "reference_docs": [],
        "category": "tech_doc",
    },
    {
        "question": "向量检索支持哪些过滤条件？",
        "ground_truth": "支持按部门(department)、密级(security_level)、文档类型(doc_type)过滤。BM25+向量双路RRF融合检索。",
        "reference_docs": [],
        "category": "tech_doc",
    },
    {
        "question": "如何处理大文件的分块？",
        "ground_truth": "Markdown按H2/H3标题分块，PDF/TXT/DOCX按800字符大小分块，重叠150字符。",
        "reference_docs": [],
        "category": "tech_doc",
    },
    {
        "question": "WebSocket在系统中的作用是什么？",
        "ground_truth": "用于实时推送文档索引进度：Python→Java Document→Browser，前端显示索引进度条。",
        "reference_docs": [],
        "category": "tech_doc",
    },
    {
        "question": "Agent模式的提示词包含哪些规则？",
        "ground_truth": "Thought→Action→Observation ReAct循环，禁止编造信息，引用文档来源，拒绝权限外问题。",
        "reference_docs": [],
        "category": "tech_doc",
    },
    # === 通用类 (general) ===
    {
        "question": "如何联系IT支持？",
        "ground_truth": "IT支持热线：分机8888，企业微信搜索'IT服务台'，或发送邮件至 itsupport@company.com。",
        "reference_docs": [],
        "category": "general",
    },
    {
        "question": "公司的组织架构是怎样的？",
        "ground_truth": "公司下设技术部、产品部、市场部、财务部、人力资源部、行政部六大部门，由CEO统一管理。",
        "reference_docs": [],
        "category": "general",
    },
    {
        "question": "会议室如何预约？",
        "ground_truth": "通过企业微信→工作台→会议室预约，选择日期和时间段，确认后系统会发送日程邀请。",
        "reference_docs": [],
        "category": "general",
    },
    {
        "question": "公司邮箱的配置方法是什么？",
        "ground_truth": "使用Outlook或Foxmail，服务器地址mail.company.com，端口IMAP 993(SSL)/SMTP 465(SSL)。",
        "reference_docs": [],
        "category": "general",
    },
    {
        "question": "VPN的连接方法是什么？",
        "ground_truth": "安装AnyConnect客户端，服务器地址 vpn.company.com，使用公司域账号和密码登录。",
        "reference_docs": [],
        "category": "general",
    },
    {
        "question": "安全培训多久进行一次？",
        "ground_truth": "每季度一次全员信息安全培训，新员工入职当月必须完成首次培训并通过考核。",
        "reference_docs": [],
        "category": "general",
    },
    {
        "question": "办公用品如何申领？",
        "ground_truth": "每月1-5日在OA系统填写申领单，部门助理统一提交，月末统一发放。紧急需求可走加急流程。",
        "reference_docs": [],
        "category": "general",
    },
    {
        "question": "访客进入公司的流程是什么？",
        "ground_truth": "提前在OA系统登记访客信息→审批→访客到前台出示身份证→领取临时工牌→接待人陪同进入。",
        "reference_docs": [],
        "category": "general",
    },
    {
        "question": "打印机如何使用？",
        "ground_truth": "连接公司WiFi后，通过 print.company.com 上传文件，在任意楼层打印机刷工卡取件。",
        "reference_docs": [],
        "category": "general",
    },
    {
        "question": "新员工入职第一天需要做什么？",
        "ground_truth": "办理入职手续→领取办公设备→参加入职培训→开通系统账号→加入部门微信群。",
        "reference_docs": [],
        "category": "general",
    },
    {
        "question": "公司WiFi的名称和密码是什么？",
        "ground_truth": "WiFi名称：Company-Office（员工用，域账号登录）、Company-Guest（访客用，前台获取密码）。",
        "reference_docs": [],
        "category": "general",
    },
    {
        "question": "公司年会的举办时间是什么？",
        "ground_truth": "每年1月中旬举办年会，具体日期由行政部提前1个月通知各部门。",
        "reference_docs": [],
        "category": "general",
    },
    {
        "question": "公司对员工着装有什么要求？",
        "ground_truth": "周一至周四商务休闲装，周五可穿便装。客户接待等正式场合需正装。",
        "reference_docs": [],
        "category": "general",
    },
    {
        "question": "如何申请加薪？",
        "ground_truth": "每年4月和10月两次调薪窗口，需由直属上级提名并结合绩效考核成绩，HR审批后执行。",
        "reference_docs": [],
        "category": "general",
    },
    {
        "question": "公司提供停车位吗？",
        "ground_truth": "地下停车场共200个车位，需在行政部登记车牌号，先到先得，月租100元。",
        "reference_docs": [],
        "category": "general",
    },
]


@dataclass
class EvalResult:
    question: str
    answer: str
    ground_truth: str
    contexts: List[str]
    latency_ms: float
    metrics: dict = field(default_factory=dict)


async def _run_single_rag(question: str, department: str = "全部", security_level: str = "内部") -> dict:
    """运行单次 RAG 查询，返回答案和上下文"""
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from rag.retriever import hybrid_search
    from llm.deepseek_client import chat_sync

    hits = hybrid_search(question, department=department, security_level=security_level, top_k=5)
    contexts = [h.get("text", "")[:500] for h in hits]

    # 构建 prompt 并调用 LLM 生成答案
    if hits:
        context_block = "\n\n---\n\n".join([
            f"[来源: {h.get('title', '')}] {h.get('text', '')[:500]}"
            for h in hits
        ])
        prompt = f"""请根据以下参考文档简要回答用户问题。只根据文档内容回答，不要编造信息。

参考文档：
{context_block}

用户问题：{question}

回答："""
        try:
            response = await chat_sync(
                messages=[{"role": "user", "content": prompt}],
                model="deepseek-v4-pro",
                temperature=0.0,
                max_tokens=300,
            )
            answer = response.content or ""
        except Exception as e:
            logger.warning(f"LLM call failed for '{question[:30]}...': {e}")
            answer = "[LLM 调用失败]"
    else:
        answer = "未找到相关信息"

    return {"answer": answer, "contexts": contexts}


def _compute_basic_metrics(result: EvalResult) -> dict:
    """计算基础评估指标（不依赖 RAGAS 库）"""
    metrics = {}

    # Context Precision: 简单字面重叠度
    if result.contexts:
        gt_words = set(result.ground_truth)
        context_text = " ".join(result.contexts)
        context_words = set(context_text)
        overlap = len(gt_words & context_words) / max(len(gt_words), 1)
        metrics["context_precision_approx"] = round(overlap, 4)

    # Answer length sanity
    metrics["answer_length"] = len(result.answer)
    metrics["answer_has_citation"] = "[来源:" in result.answer or "《" in result.answer

    # Latency
    metrics["latency_ms"] = round(result.latency_ms, 0)

    return metrics


async def run_evaluation(
    test_cases: Optional[List[dict]] = None,
    output_file: Optional[str] = None,
) -> List[EvalResult]:
    """运行完整评估流程"""
    cases = test_cases or DEFAULT_TEST_CASES
    results: List[EvalResult] = []

    print(f"\n{'='*60}")
    print(f"RAG Evaluation — {len(cases)} test cases")
    print(f"{'='*60}\n")

    for i, case in enumerate(cases, 1):
        question = case["question"]
        ground_truth = case.get("ground_truth", "")

        start = time.time()
        rag_result = await _run_single_rag(question)
        latency_ms = (time.time() - start) * 1000

        result = EvalResult(
            question=question,
            answer=rag_result["answer"],
            ground_truth=ground_truth,
            contexts=rag_result["contexts"],
            latency_ms=latency_ms,
        )
        result.metrics = _compute_basic_metrics(result)
        results.append(result)

        status = "OK" if result.metrics.get("answer_has_citation") else "N/A"
        print(f"[{i:2d}/{len(cases)}] {status} | {latency_ms:.0f}ms | {question[:40]}...")

    # ── 汇总统计 ──
    print(f"\n{'='*60}")
    print("Evaluation Summary")
    print(f"{'='*60}")

    total = len(results)
    answered = sum(1 for r in results if r.answer and "[LLM 调用失败]" not in r.answer and r.answer != "未找到相关信息")
    cited = sum(1 for r in results if r.metrics.get("answer_has_citation"))
    avg_latency = sum(r.latency_ms for r in results) / max(total, 1)
    avg_answer_len = sum(r.metrics.get("answer_length", 0) for r in results) / max(total, 1)
    avg_cp = sum(r.metrics.get("context_precision_approx", 0) for r in results) / max(total, 1)

    print(f"Total cases:      {total}")
    print(f"Answered:         {answered}/{total} ({answered*100//total}%)")
    print(f"With citations:   {cited}/{total} ({cited*100//total}%)")
    print(f"Avg latency:      {avg_latency:.0f}ms")
    print(f"Avg answer len:   {avg_answer_len:.0f} chars")
    print(f"Avg context prec: {avg_cp:.4f} (approx)")
    print()

    # ── 导出 ──
    if output_file:
        report = {
            "summary": {
                "total": total,
                "answered": answered,
                "answered_rate": f"{answered*100//total}%",
                "with_citations": cited,
                "avg_latency_ms": round(avg_latency, 0),
                "avg_answer_length": round(avg_answer_len, 0),
                "avg_context_precision_approx": round(avg_cp, 4),
            },
            "details": [
                {
                    "question": r.question,
                    "answer": r.answer[:300],
                    "ground_truth": r.ground_truth[:200],
                    "contexts": r.contexts[:3],
                    "latency_ms": r.metrics.get("latency_ms", 0),
                    "context_precision_approx": r.metrics.get("context_precision_approx", 0),
                    "has_citation": r.metrics.get("answer_has_citation", False),
                }
                for r in results
            ],
        }
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"Report saved to: {output_file}")

    return results


async def _try_ragas(results: List[EvalResult]):
    """尝试使用 RAGAS 库计算完整四维指标"""
    try:
        from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
        from ragas import evaluate
        from datasets import Dataset

        dataset = Dataset.from_dict({
            "question": [r.question for r in results],
            "answer": [r.answer for r in results],
            "contexts": [r.contexts for r in results],
            "ground_truth": [r.ground_truth for r in results],
        })

        ragas_result = evaluate(
            dataset,
            metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        )

        print("\nRAGAS Metrics:")
        print("-" * 40)
        for key, val in ragas_result.items():
            print(f"  {key}: {val:.4f}")
        print()

        return dict(ragas_result)
    except ImportError:
        print("\n[RAGAS not installed] Install with: pip install ragas datasets")
        print("Showing approximate metrics only.\n")
        return {}


async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-file", type=str, help="JSON test cases file")
    parser.add_argument("--output", "-o", type=str, default="eval_report.json", help="Output report file")
    parser.add_argument("--ragas", action="store_true", help="Attempt RAGAS evaluation")
    args = parser.parse_args()

    cases = DEFAULT_TEST_CASES
    if args.test_file and os.path.exists(args.test_file):
        with open(args.test_file, "r", encoding="utf-8") as f:
            cases = json.load(f)
        print(f"Loaded {len(cases)} test cases from {args.test_file}")

    results = await run_evaluation(cases, output_file=args.output)

    if args.ragas:
        await _try_ragas(results)


if __name__ == "__main__":
    asyncio.run(main())
