import random
import re

# ===========================
# 模拟 LLM（Fake LLM）
# ===========================
def fake_llm(prompt: str, temperature=0.0) -> str:
    """
    模拟一个不完美的 LLM：
    - 如果 prompt 中包含“只回答”，则严格输出“奇数”或“偶数”
    - 否则可能输出带解释的句子（导致格式错误）
    - 对负数和0也能正确处理
    """
    # 提取数字
    num_match = re.search(r'-?\d+', prompt)
    if not num_match:
        return "无法识别数字"
    num = int(num_match.group())

    is_even = (num % 2 == 0)
    base_answer = "偶数" if is_even else "奇数"

    # 如果指令强调“只回答”，就干净输出
    if "只回答" in prompt or "仅输出" in prompt or "简洁" in prompt:
        return base_answer
    else:
        # 否则可能啰嗦（模拟真实 LLM 的不稳定性）
        templates = [
            f"{num} 是 {base_answer}。",
            f"这个数是{base_answer}",
            base_answer,
            f"答案：{base_answer}",
            f"我认为这是{base_answer}。"
        ]
        # temperature > 0 时引入随机性
        if temperature > 0:
            return random.choice(templates)
        else:
            # deterministic: 有时干净，有时啰嗦
            return templates[num % len(templates)]

# ===========================
# 验证集（多样化测试用例）
# ===========================
VALIDATION_SET = [
    (0, "偶数"),
    (1, "奇数"),
    (2, "偶数"),
    (-3, "奇数"),
    (100, "偶数"),
    (999, "奇数"),
    (-8, "偶数")
]

# ===========================
# 评估函数：计算准确率
# ===========================
def evaluate_prompt(prompt_template: str, validation_set=VALIDATION_SET) -> float:
    correct = 0
    for num, expected in validation_set:
        full_input = prompt_template.format(number=num)
        response = fake_llm(full_input, temperature=0.0)
        predicted = response.strip()
        # 只有完全匹配才算对（严格模式）
        if predicted == expected:
            correct += 1
    return correct / len(validation_set)

# ===========================
# APE 主循环：支持多轮迭代
# ===========================
def automatic_prompt_engineer(
        task_description: str,
        initial_instructions: list,
        validation_set=VALIDATION_SET,
        max_iterations=3,
        top_k=2  # 每轮保留 top-k prompts 用于生成下一代
):
    print("🚀 启动 Automatic Prompt Engineer (APE)...\n")

    # 第0轮：初始候选
    current_candidates = initial_instructions.copy()

    for iteration in range(max_iterations):
        print(f"🔁 迭代 {iteration + 1}/{max_iterations}")
        print("-" * 50)

        # 评估当前所有候选
        scored_prompts = []
        for prompt in current_candidates:
            acc = evaluate_prompt(prompt, validation_set)
            scored_prompts.append((prompt, acc))
            print(f"Prompt: {prompt}\n准确率: {acc:.2%}\n")

        # 按准确率排序，选 top-k
        scored_prompts.sort(key=lambda x: x[1], reverse=True)
        top_prompts = [p for p, _ in scored_prompts[:top_k]]
        best_acc = scored_prompts[0][1]
        best_prompt = scored_prompts[0][0]

        print(f"🏆 当前最佳准确率: {best_acc:.2%}")
        print(f"   最佳 Prompt: {best_prompt}\n")

        # 如果已经 100%，提前收敛
        if best_acc >= 1.0:
            print("✅ 已达到完美准确率，提前收敛！")
            return best_prompt

        # 如果不是最后一轮，生成下一代候选
        if iteration < max_iterations - 1:
            next_candidates = set(top_prompts)  # 保留精英

            # 让“模拟 LLM”基于高分 prompt 改写新版本（简化版）
            for prompt in top_prompts:
                # 简单改写策略：添加/替换关键词
                variants = [
                    prompt.replace("判断", "请判断").replace("。", "，请只回答“奇数”或“偶数”。"),
                    "请分析以下数字的奇偶性，并仅输出一个词：“奇数”或“偶数”。输入：{number}",
                    "这个数是奇数还是偶数？简洁回答。输入：{number}",
                    "仅输出“奇数”或“偶数”：输入：{number}"
                ]
                next_candidates.update(variants)

            current_candidates = list(next_candidates)
            print(f"➡️ 生成 {len(current_candidates)} 个新候选进入下一轮。\n")

    return best_prompt

# ===========================
# 启动 APE
# ===========================
if __name__ == "__main__":
    # 初始种子 prompts（模拟第一轮 LLM 生成）
    seeds = [
        "判断以下数字是奇数还是偶数。输入：{number}",
        "这个数是奇数还是偶数？输入：{number}",
        "分析该整数的奇偶性。输入：{number}",
        "告诉我 {number} 是偶数还是奇数。"
    ]

    final_prompt = automatic_prompt_engineer(
        task_description="判断整数奇偶性",
        initial_instructions=seeds,
        max_iterations=3,
        top_k=2
    )

    print("\n" + "="*60)
    print("🎯 最终选出的最佳 Prompt:")
    print(final_prompt)