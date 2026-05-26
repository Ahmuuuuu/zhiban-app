"""创建演示用户：用户名 1，密码 11111111，含完整画像 + 雷达数据"""
import asyncio
import json
import sys
sys.path.insert(0, ".")

from backend.src.utils.database import init_db, close_db
from backend.src.utils.pwintohash import get_password_hash
from backend.src.models.usermodel import User
from backend.src.models.portraitmodel import User_picture
from backend.src.models.exam_model import ExamQuestion, ExamRecord, KnowledgeMastery
from backend.src.models.portrait_radar_model import PortraitRadar


async def setup():
    await init_db()

    # ── 删除旧用户 ──
    old = await User.filter(username="1").first()
    if old:
        await old.delete()
        print("已删除旧用户 1")

    # ── 创建用户 ──
    user = await User.create(
        username="1",
        password=get_password_hash("11111111"),
        university="清华大学",
        grade="大三",
        major="计算机科学与技术",
        profile="热爱编程的CS学生，对AI和算法方向感兴趣",
    )
    print(f"创建用户: id={user.id}, username={user.username}")

    # ── 创建画像 ──
    picture = await User_picture.create()
    traits = {
        "knowbase": {"value": "3.5", "confidence": 0.85, "source": "agent_inferred"},
        "commonmis": {"value": "动态规划状态转移、指针操作、时间复杂度分析", "confidence": 0.75, "source": "agent_inferred"},
        "learning_pace": {"value": "偏好先理解原理再动手实践，喜欢系统化学习", "confidence": 0.80, "source": "user_stated"},
        "interest": {"value": "机器学习、算法设计、系统架构", "confidence": 0.90, "source": "user_stated"},
        "strengths": {"value": "Python编程、数据结构基础、数学功底扎实", "confidence": 0.85, "source": "agent_inferred"},
        "weaknesses": {"value": "动态规划、并发编程、系统设计", "confidence": 0.75, "source": "agent_inferred"},
        "knowledge_mastery": [
            {"tag": "Python基础", "level": "mastered", "accuracy": 0.95},
            {"tag": "Python面向对象", "level": "proficient", "accuracy": 0.82},
            {"tag": "列表与字典", "level": "mastered", "accuracy": 0.90},
            {"tag": "数组与字符串", "level": "mastered", "accuracy": 0.88},
            {"tag": "链表", "level": "proficient", "accuracy": 0.75},
            {"tag": "栈与队列", "level": "proficient", "accuracy": 0.78},
            {"tag": "二叉树", "level": "learning", "accuracy": 0.65},
            {"tag": "二叉搜索树", "level": "learning", "accuracy": 0.55},
            {"tag": "哈希表", "level": "proficient", "accuracy": 0.72},
            {"tag": "图论基础", "level": "learning", "accuracy": 0.60},
            {"tag": "DFS与BFS", "level": "learning", "accuracy": 0.58},
            {"tag": "排序算法", "level": "proficient", "accuracy": 0.80},
            {"tag": "快速排序", "level": "proficient", "accuracy": 0.76},
            {"tag": "归并排序", "level": "learning", "accuracy": 0.62},
            {"tag": "动态规划", "level": "beginner", "accuracy": 0.35},
            {"tag": "贪心算法", "level": "beginner", "accuracy": 0.40},
            {"tag": "回溯算法", "level": "beginner", "accuracy": 0.30},
            {"tag": "时间复杂度分析", "level": "learning", "accuracy": 0.55},
            {"tag": "空间复杂度", "level": "learning", "accuracy": 0.50},
            {"tag": "递归", "level": "proficient", "accuracy": 0.78},
            {"tag": "位运算", "level": "beginner", "accuracy": 0.25},
            {"tag": "滑动窗口", "level": "beginner", "accuracy": 0.20},
            {"tag": "双指针", "level": "proficient", "accuracy": 0.75},
            {"tag": "前缀和", "level": "learning", "accuracy": 0.55},
            {"tag": "单调栈", "level": "beginner", "accuracy": 0.15},
            {"tag": "并查集", "level": "beginner", "accuracy": 0.10},
            {"tag": "Trie树", "level": "beginner", "accuracy": 0.05},
            {"tag": "线段树", "level": "beginner", "accuracy": 0.0},
            {"tag": "最短路径Dijkstra", "level": "learning", "accuracy": 0.52},
            {"tag": "最小生成树", "level": "beginner", "accuracy": 0.18},
        ],
    }
    picture.traits = json.dumps(traits, ensure_ascii=False)
    picture.cognition = "visual"
    picture.learning_goal = "job"
    picture.personality_tags = json.dumps(["逻辑清晰", "喜欢动手实践", "自驱力强", "偶尔急躁"], ensure_ascii=False)
    picture.profile_summary = "该生具备扎实的编程基础和数学功底，擅长Python和数据结构的常规操作。但在高阶算法（动态规划、贪心、回溯）和系统设计方面明显薄弱，需要系统性的算法训练和项目实战。偏好视觉化学习，目标是求职面试准备。"
    await picture.save()

    user.picture = picture
    await user.save()
    print("画像初始化完成")

    # ── 创建题库 ──
    questions_data = [
        # easy - 基础题
        {"question_type": "single_choice", "content": "Python中列表(list)和元组(tuple)的主要区别是什么？", "options": ["A. 列表可变，元组不可变", "B. 列表不可变，元组可变", "C. 两者完全相同", "D. 列表只能存数字"], "answer": "A", "analysis": "列表(list)是可变的，可以增删改元素；元组(tuple)是不可变的。", "difficulty": "easy", "knowledge_tags": ["Python基础"]},
        {"question_type": "single_choice", "content": "以下哪个数据结构是LIFO（后进先出）？", "options": ["A. 队列", "B. 栈", "C. 链表", "D. 哈希表"], "answer": "B", "analysis": "栈(Stack)遵循后进先出(LIFO)原则，队列遵循先进先出(FIFO)。", "difficulty": "easy", "knowledge_tags": ["栈与队列"]},
        {"question_type": "single_choice", "content": "Python中dict的键(key)必须是什么类型？", "options": ["A. 只能是字符串", "B. 只能是整数", "C. 必须是不可变类型(hashable)", "D. 任意类型都可以"], "answer": "C", "analysis": "字典的键必须是不可变(hashable)类型，如字符串、数字、元组等。", "difficulty": "easy", "knowledge_tags": ["哈希表"]},
        {"question_type": "single_choice", "content": "以下哪种排序算法平均时间复杂度为O(n log n)？", "options": ["A. 冒泡排序", "B. 选择排序", "C. 快速排序", "D. 插入排序"], "answer": "C", "analysis": "快速排序平均时间复杂度为O(n log n)，冒泡/选择/插入排序为O(n²)。", "difficulty": "easy", "knowledge_tags": ["排序算法", "时间复杂度分析"]},
        {"question_type": "single_choice", "content": "递归函数必须包含什么？", "options": ["A. 循环语句", "B. 终止条件(基线条件)", "C. 全局变量", "D. try-except块"], "answer": "B", "analysis": "递归函数必须包含终止条件（基线条件），否则会导致无限递归。", "difficulty": "easy", "knowledge_tags": ["递归"]},
        # medium - 中等题
        {"question_type": "single_choice", "content": "在二叉搜索树中，中序遍历的结果是什么？", "options": ["A. 无序序列", "B. 降序序列", "C. 升序序列", "D. 层序序列"], "answer": "C", "analysis": "二叉搜索树(BST)的性质决定了中序遍历得到的是升序序列。", "difficulty": "medium", "knowledge_tags": ["二叉搜索树", "二叉树"]},
        {"question_type": "multi_choice", "content": "以下哪些是解决哈希冲突的方法？", "options": ["A. 链地址法", "B. 开放地址法", "C. 深度优先搜索", "D. 再哈希法"], "answer": ["A", "B", "D"], "analysis": "哈希冲突解决方法包括链地址法、开放地址法（线性探测/二次探测）、再哈希法等。DFS是图遍历算法。", "difficulty": "medium", "knowledge_tags": ["哈希表"]},
        {"question_type": "single_choice", "content": "DFS遍历图时，使用什么辅助数据结构？", "options": ["A. 队列", "B. 栈或递归", "C. 堆", "D. 哈希表"], "answer": "B", "analysis": "DFS（深度优先搜索）使用栈（显式或递归调用栈）。BFS用队列。", "difficulty": "medium", "knowledge_tags": ["DFS与BFS", "图论基础"]},
        {"question_type": "multi_choice", "content": "以下哪些算法的思想属于'分治法'？", "options": ["A. 归并排序", "B. 快速排序", "C. 冒泡排序", "D. 二分查找"], "answer": ["A", "B", "D"], "analysis": "归并排序、快速排序、二分查找都使用了分治思想。冒泡排序是简单的比较交换。", "difficulty": "medium", "knowledge_tags": ["排序算法", "归并排序", "快速排序"]},
        {"question_type": "single_choice", "content": "在动态规划中，'最优子结构'指的是什么？", "options": ["A. 每个子问题都相同", "B. 问题的最优解包含子问题的最优解", "C. 子问题之间相互独立", "D. 问题可以用贪心策略解决"], "answer": "B", "analysis": "最优子结构指原问题的最优解可以通过子问题的最优解来构造。", "difficulty": "medium", "knowledge_tags": ["动态规划"]},
        {"question_type": "single_choice", "content": "双指针技巧在以下哪个场景中最常用？", "options": ["A. 二叉树遍历", "B. 有序数组的两数之和", "C. 图的拓扑排序", "D. 哈希查找"], "answer": "B", "analysis": "双指针常用于有序数组中查找满足条件的元素对，如两数之和、三数之和等。", "difficulty": "medium", "knowledge_tags": ["双指针"]},
        # hard - 困难题
        {"question_type": "single_choice", "content": "给定n个物品和容量W的背包，0-1背包问题的动态规划时间复杂度是多少？", "options": ["A. O(n)", "B. O(W)", "C. O(nW)", "D. O(2^n)"], "answer": "C", "analysis": "0-1背包DP解法时间复杂度为O(nW)，其中n为物品数，W为背包容量。注意这是伪多项式时间。", "difficulty": "hard", "knowledge_tags": ["动态规划", "时间复杂度分析"]},
        {"question_type": "multi_choice", "content": "Dijkstra算法不能处理以下哪些情况？", "options": ["A. 有向图", "B. 负权边", "C. 负权环", "D. 带权无向图"], "answer": ["B", "C"], "analysis": "Dijkstra算法要求边权非负，不能处理负权边和负权环。可以处理有向图和无向图。", "difficulty": "hard", "knowledge_tags": ["最短路径Dijkstra", "图论基础"]},
        {"question_type": "single_choice", "content": "线段树在区间查询场景下，单次查询的时间复杂度是多少？", "options": ["A. O(1)", "B. O(log n)", "C. O(n)", "D. O(n log n)"], "answer": "B", "analysis": "线段树区间查询的时间复杂度为O(log n)，这是它相比暴力O(n)的主要优势。", "difficulty": "hard", "knowledge_tags": ["线段树"]},
        {"question_type": "single_choice", "content": "回溯算法解决N皇后问题的时间复杂度最接近以下哪个？", "options": ["A. O(N)", "B. O(N²)", "C. O(N!)", "D. O(2^N)"], "answer": "C", "analysis": "N皇后问题的时间复杂度约为O(N!)，因为每行选择一个位置后，下一行可选位置减少。", "difficulty": "hard", "knowledge_tags": ["回溯算法"]},
    ]

    created_questions = []
    for q in questions_data:
        eq = await ExamQuestion.create(
            question_type=q["question_type"],
            content=q["content"],
            options=json.dumps(q["options"], ensure_ascii=False) if q.get("options") else None,
            answer=json.dumps(q["answer"], ensure_ascii=False) if isinstance(q["answer"], list) else q["answer"],
            analysis=q.get("analysis", ""),
            difficulty=q["difficulty"],
            knowledge_tags=json.dumps(q["knowledge_tags"], ensure_ascii=False),
            is_public=True,
            user=user,
        )
        created_questions.append(eq)
    print(f"题库创建完成: {len(created_questions)} 道题")

    # ── 创建答题记录（模拟多天答题历史，使雷达数据更真实）──
    from datetime import datetime, timedelta
    import random
    random.seed(42)

    # 模拟近30天的答题活动
    exam_sessions: list[list] = []  # [(offset_days, [(q_idx, is_correct), ...])]
    for day_offset in range(30, 0, -1):  # 30天前到昨天
        if random.random() < 0.35:  # 约35%的天数有答题（~10天活跃）
            continue
        session_questions = random.sample(range(len(created_questions)), min(6, len(created_questions)))
        session = []
        for qi in session_questions:
            q = created_questions[qi]
            # 根据难度调整正确率: easy 80%, medium 55%, hard 30%
            diff = q.difficulty
            if diff == "easy":
                correct = random.random() < 0.80
            elif diff == "medium":
                correct = random.random() < 0.55
            else:
                correct = random.random() < 0.30
            session.append((qi, correct))
        exam_sessions.append((day_offset, session))

    # 创建答题记录（分散在近30天内）
    now = datetime.now()
    for day_offset, session in exam_sessions:
        session_id = f"demo_session_{day_offset}"
        base_time = now - timedelta(days=day_offset)
        for qi, correct in session:
            record_time = base_time + timedelta(minutes=random.randint(1, 30))
            q = created_questions[qi]
            correct_answer = json.loads(q.answer) if q.answer.startswith("[") else q.answer
            await ExamRecord.create(
                user_answer=correct_answer if correct else "错误答案",
                is_correct=correct,
                score=100 if correct else 0,
                time_spent=random.randint(30, 300),
                session_id=session_id,
                question=q,
                user=user,
                created_at=record_time,
            )

    # 统计答题记录
    record_count = await ExamRecord.filter(user_id=user.id).count()
    print(f"答题记录创建完成: {record_count} 条")

    # ── 创建 KnowledgeMastery 记录 ──
    # 从 traits 中的 knowledge_mastery 同步到 KnowledgeMastery 表
    for km in traits["knowledge_mastery"]:
        level_map = {"mastered": 4, "proficient": 3, "learning": 2, "beginner": 1}
        total = random.randint(3, 15)
        correct = int(total * km["accuracy"])
        await KnowledgeMastery.create(
            user=user,
            knowledge_tag=km["tag"],
            mastery_level=km["level"],
            total_attempts=total,
            correct_count=correct,
        )
    print(f"KnowledgeMastery 创建完成: {len(traits['knowledge_mastery'])} 条")

    # ── 初始化雷达 ──
    from backend.src.service.portrait_service import PortraitRadarService
    try:
        radar = await PortraitRadarService.compute(user.id)
        print("雷达数据计算完成:")
        for d in radar["dimensions"]:
            print(f"  {d['label']}: {d['score']}")
    except Exception as e:
        print(f"雷达计算失败: {e}")

    await close_db()
    print("\n=== 演示用户创建完成 ===")
    print(f"用户名: 1")
    print(f"密码: 11111111")
    print(f"用户ID: {user.id}")


if __name__ == "__main__":
    asyncio.run(setup())
