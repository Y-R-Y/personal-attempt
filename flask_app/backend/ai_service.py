"""
DeepSeek AI 服务模块
提供AI智能解析、学习计划生成、学习报告等功能
"""

import os
from openai import OpenAI
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class DeepSeekService:
    """DeepSeek AI服务类"""
    
    def __init__(self):
        """初始化DeepSeek客户端"""
        api_key = os.getenv('DEEPSEEK_API_KEY')
        base_url = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com/v1')
        
        if not api_key or api_key == 'your_api_key_here':
            raise ValueError("请配置 DEEPSEEK_API_KEY 环境变量")
        
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self.model = os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')
    
    def explain_question(self, question, user_answer, correct_answer, subject, question_type='choice'):
        """
        AI解析题目
        
        Args:
            question: 题目内容
            user_answer: 学生答案
            correct_answer: 正确答案
            subject: 科目名称
            question_type: 题目类型（choice/fill）
            
        Returns:
            str: AI生成的解析内容
        """
        # 科目中文名称映射
        subject_names = {
            'math': '数学',
            'chinese': '语文',
            'english': '英语',
            'science': '科学',
            'history': '历史'
        }
        subject_cn = subject_names.get(subject, subject)
        
        prompt = f"""你是一位专业且亲切的小学教师，擅长用简单易懂的语言为小学生讲解题目。

请解析这道{subject_cn}题：

**题目：** {question}
**学生答案：** {user_answer if user_answer else '未作答'}
**正确答案：** {correct_answer}

请按照以下结构提供解析（使用emoji增加趣味性）：

🎯 **解题思路**
分步骤详细说明如何解这道题，让小学生能轻松理解。

📚 **知识点**
列出这道题涉及的核心知识点。

❌ **常见错误**
分析学生可能犯的错误及原因。

💡 **举一反三**
出一道类似的题目供学生练习（只需出题，不需要给答案）。

要求：
- 语言要亲切、生动，适合7-12岁的小学生理解
- 使用适当的emoji让内容更有趣
- 避免使用过于专业的术语
- 如果学生答对了，也要给予鼓励
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一位专业且亲切的小学教师，擅长用简单易懂的方式为小学生讲解题目。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=800
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"AI解析失败: {str(e)}")
            raise
    
    def generate_study_plan(self, user_stats, weak_points, recent_performance):
        """
        生成个性化学习计划
        
        Args:
            user_stats: 用户统计数据（总答题数、正确率等）
            weak_points: 薄弱知识点列表
            recent_performance: 近期表现数据
            
        Returns:
            str: AI生成的学习计划
        """
        prompt = f"""你是一位经验丰富的小学教育专家，请根据以下学生数据制定今天的学习计划：

**学生概况：**
- 总答题数：{user_stats.get('total_questions', 0)} 题
- 总体正确率：{user_stats.get('accuracy', 0)}%
- 连续学习天数：{user_stats.get('consecutive_days', 0)} 天

**薄弱科目/知识点：**
{', '.join(weak_points) if weak_points else '暂无明显薄弱点'}

**近期表现：**
{recent_performance}

请制定一份合理可行的今日学习计划，包含：

📅 **今日学习目标**
设定具体、可量化的学习目标（例如：完成15道数学题，正确率达到80%以上）

📝 **推荐练习安排**
- 各科目的练习题目数量
- 建议的练习顺序
- 预计用时

🎯 **重点复习内容**
针对薄弱知识点，给出具体的复习建议

⭐ **鼓励话语**
给学生一段温暖的鼓励，激发学习动力

要求：
- 计划要合理可行，不要给学生太大压力
- 考虑小学生的注意力持续时间（建议每次练习不超过20分钟）
- 平衡各科目，避免偏科
- 语气要温暖、积极、鼓励性
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一位经验丰富的小学教育专家，擅长为学生制定个性化的学习计划。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=600
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"生成学习计划失败: {str(e)}")
            raise
    
    def generate_learning_report(self, weekly_data):
        """
        生成周度学习报告（给家长看）
        
        Args:
            weekly_data: 本周学习数据
            
        Returns:
            str: AI生成的学习报告
        """
        prompt = f"""你是一位专业的小学教育顾问，请根据以下本周学习数据，为家长生成一份温暖、专业的学习报告：

**本周学习数据：**
- 答题总数：{weekly_data.get('total_questions', 0)} 题
- 平均正确率：{weekly_data.get('accuracy', 0)}%
- 学习时长：{weekly_data.get('study_time', 0)} 分钟
- 活跃天数：{weekly_data.get('active_days', 0)} / 7 天

**各科表现：**
{weekly_data.get('subject_performance', '暂无详细数据')}

**进步情况：**
{weekly_data.get('improvement', '数据不足')}

请生成一份给家长的学习报告，包含以下内容：

📊 **本周学习总结**
简要概述孩子本周的整体学习情况

🌟 **亮点与进步**
表扬孩子的进步和做得好的地方（要具体）

⚠️ **需要关注的地方**
温和地指出需要改进的方面，并给出建议

💡 **下周建议**
给出具体可行的下周学习建议

💬 **给家长的建议**
提供一些家庭教育方面的建议

要求：
- 语气要专业但温暖，既肯定进步又指出不足
- 避免使用过于负面的词汇
- 建议要具体、可操作
- 长度适中，便于家长快速阅读
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一位专业的小学教育顾问，擅长为家长生成温暖、专业的学习报告。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=800
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"生成学习报告失败: {str(e)}")
            raise
    
    def correct_essay(self, essay_text, grade_level, essay_type='narrative'):
        """
        AI作文批改
        
        Args:
            essay_text: 学生作文内容
            grade_level: 年级（1-6）
            essay_type: 作文类型（narrative/descriptive/argumentative）
            
        Returns:
            str: AI生成的批改意见
        """
        type_names = {
            'narrative': '记叙文',
            'descriptive': '描写文',
            'argumentative': '议论文'
        }
        type_cn = type_names.get(essay_type, '作文')
        
        prompt = f"""你是一位经验丰富的小学语文教师，请批改这篇{grade_level}年级学生的{type_cn}。

**学生作文：**
{essay_text}

请从以下几个方面进行详细批改：

📝 **总体评价**
对整篇作文给出总体评价和鼓励。

✨ **优点亮点**
列出作文中的优点和亮点（至少3点）。

⚠️ **需要改进**
指出需要改进的地方（最多3点），并给出具体建议。

🔤 **字词纠错**
如果有错别字或用词不当，请指出并改正。

💡 **提升建议**
给出2-3条具体的写作提升建议。

⭐ **评分**
给出百分制评分，并说明评分理由。

要求：
- 语气要温暖、鼓励性，保护学生的写作兴趣
- 建议要具体、可操作
- 适合{grade_level}年级学生的水平
- 使用emoji让批改更生动有趣
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一位经验丰富且温暖的小学语文教师，擅长批改学生作文。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"作文批改失败: {str(e)}")
            raise
    
    def practice_speaking(self, topic, difficulty='medium', language='english'):
        """
        AI口语练习
        
        Args:
            topic: 练习话题
            difficulty: 难度（easy/medium/hard）
            language: 语言（english/chinese）
            
        Returns:
            dict: 包含对话场景、问题、示例回答等
        """
        lang_name = '英语' if language == 'english' else '中文'
        diff_names = {
            'easy': '简单',
            'medium': '中等',
            'hard': '困难'
        }
        diff_cn = diff_names.get(difficulty, '中等')
        
        prompt = f"""你是一位专业的{lang_name}口语教练，请为小学生设计一个口语练习场景。

**练习主题：** {topic}
**难度级别：** {diff_cn}
**目标语言：** {lang_name}

请设计以下内容：

🎭 **场景设定**
创建一个有趣的对话场景（例如：在商店购物、在学校交朋友、在餐厅点餐等）。

👥 **角色分配**
设定两个角色（学生和对话伙伴）。

💬 **对话开始**
由对话伙伴说出第一句话，引导学生开口。

❓ **引导问题**
提供3-5个循序渐进的问题，帮助学生展开对话。

✅ **示例回答**
为每个问题提供一个简单的示例回答（适合小学生水平）。

🌟 **常用表达**
列出5-8个这个场景中常用的表达方式。

💡 **发音提示**
如果有难读的词，给出音标或发音提示。

要求：
- 场景要贴近小学生的生活
- 语言难度适合{diff_cn}级别
- 内容有趣、能激发学生兴趣
- 如果是英语，同时提供中文翻译
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": f"你是一位专业的{lang_name}口语教练，擅长为小学生设计有趣的口语练习。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"口语练习生成失败: {str(e)}")
            raise
    
    def recommend_questions(self, user_stats, weak_points, preferred_subjects):
        """
        AI智能推荐题目
        
        Args:
            user_stats: 用户统计数据
            weak_points: 薄弱知识点
            preferred_subjects: 偏好的科目
            
        Returns:
            list: 推荐的题目列表（包含题目内容和推荐理由）
        """
        prompt = f"""你是一位智能学习顾问，请根据学生的学习情况推荐适合的练习题。

**学生概况：**
- 总答题数：{user_stats.get('total_questions', 0)} 题
- 总体正确率：{user_stats.get('accuracy', 0)}%
- 当前等级：{user_stats.get('level', 1)} 年级

**薄弱知识点：**
{', '.join(weak_points) if weak_points else '暂无明显薄弱点'}

**偏好科目：**
{', '.join(preferred_subjects) if preferred_subjects else '无特定偏好'}

请推荐5道练习题，每道题包含：

1️⃣ **题目内容**
具体的题目描述

2️⃣ **科目和难度**
标注科目和难度等级（1-3星）

3️⃣ **推荐理由**
为什么推荐这道题（针对薄弱点、巩固基础、挑战提升等）

4️⃣ **预期收获**
完成这道题能学到什么

要求：
- 题目难度要适中，既不能太简单也不能太难
- 优先推荐薄弱知识点的题目
- 兼顾学生偏好的科目
- 题目类型多样化（选择题、填空题等）
- 适合小学生的认知水平
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一位智能学习顾问，擅长根据学生情况推荐个性化的练习题。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1200
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"题目推荐失败: {str(e)}")
            raise
    
    def generate_knowledge_graph(self, subject, topics):
        """
        AI生成知识点图谱
        
        Args:
            subject: 科目名称
            topics: 知识点列表
            
        Returns:
            str: 知识点之间的关系和结构
        """
        subject_names = {
            'math': '数学',
            'chinese': '语文',
            'english': '英语',
            'science': '科学',
            'history': '历史'
        }
        subject_cn = subject_names.get(subject, subject)
        
        prompt = f"""你是一位{subject_cn}教育专家，请为学生梳理以下知识点之间的关系，形成知识图谱。

**科目：** {subject_cn}
**知识点列表：**
{chr(10).join([f'- {topic}' for topic in topics])}

请按照以下结构整理：

🗺️ **知识图谱概览**
用文字描述这些知识点之间的层次关系和联系。

📊 **知识结构**
将知识点分为：
- 基础概念（必须先掌握的）
- 核心技能（重点学习的）
- 拓展应用（进阶内容）

🔗 **知识点关联**
说明各个知识点之间的联系：
- A知识点是B知识点的基础
- C知识点需要D知识点作为前提
- E和F可以一起学习

📈 **学习路径建议**
给出一个合理的学习顺序建议。

⚠️ **常见误区**
指出学生在学习这些知识点时容易混淆或出错的地方。

💡 **学习技巧**
提供2-3个高效学习这些知识点的技巧。

要求：
- 结构清晰，便于学生理解
- 用简单的语言解释复杂的关系
- 适合小学生的认知水平
- 使用图表符号让内容更直观
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": f"你是一位{subject_cn}教育专家，擅长梳理知识点之间的关系。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.6,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"知识图谱生成失败: {str(e)}")
            raise
    
    def chat_with_ai(self, user_message, conversation_history=None, context='learning'):
        """
        AI学习伙伴（智能问答）
        
        Args:
            user_message: 用户消息
            conversation_history: 对话历史（可选）
            context: 对话上下文（learning/homework/fun）
            
        Returns:
            str: AI的回复
        """
        context_names = {
            'learning': '学习辅导',
            'homework': '作业帮助',
            'fun': '轻松聊天'
        }
        context_cn = context_names.get(context, '学习辅导')
        
        # 构建对话历史
        messages = [
            {"role": "system", "content": f"""你是一位友善、耐心的AI学习伙伴，专门为小学生提供帮助。

你的特点：
- 说话亲切、友好，像一个大哥哥/大姐姐
- 用简单易懂的语言解释问题
- 鼓励学生思考，而不是直接给答案
- 适当使用emoji让对话更有趣
- 如果不知道答案，诚实地告诉学生
- 保持积极向上的态度

当前对话场景：{context_cn}"""}
        ]
        
        # 添加对话历史
        if conversation_history:
            messages.extend(conversation_history[-10:])  # 只保留最近10条
        
        # 添加当前消息
        messages.append({"role": "user", "content": user_message})
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.8,
                max_tokens=500
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"AI对话失败: {str(e)}")
            raise
    
    def generate_practice_questions(self, subject, topic, difficulty, count=5):
        """
        AI自动生成练习题
        
        Args:
            subject: 科目
            topic: 知识点/主题
            difficulty: 难度（1-3）
            count: 题目数量
            
        Returns:
            list: 生成的题目列表
        """
        subject_names = {
            'math': '数学',
            'chinese': '语文',
            'english': '英语',
            'science': '科学',
            'history': '历史'
        }
        subject_cn = subject_names.get(subject, subject)
        
        diff_names = {
            1: '简单（一年级水平）',
            2: '中等（二三年级水平）',
            3: '困难（四五年级水平）'
        }
        diff_cn = diff_names.get(difficulty, '中等')
        
        prompt = f"""你是一位专业的{subject_cn}教师，请生成{count}道关于"{topic}"的练习题。

**科目：** {subject_cn}
**知识点：** {topic}
**难度：** {diff_cn}
**题目数量：** {count}道

请生成题目，每道题包含：

**题目X：**
- 题型：（选择题/填空题/判断题）
- 题目内容：
- 选项：（如果是选择题，提供4个选项）
- 正确答案：
- 解析：（简要说明解题思路）

要求：
- 题目难度适合{diff_cn}
- 围绕"{topic}"这个知识点
- 题型多样化
- 答案准确无误
- 解析简明扼要
- 适合小学生理解
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": f"你是一位专业的{subject_cn}教师，擅长出题。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.9,
                max_tokens=1500
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"题目生成失败: {str(e)}")
            raise


# 测试代码
if __name__ == '__main__':
    # 测试AI服务
    try:
        service = DeepSeekService()
        print("✅ DeepSeek服务初始化成功")
        
        # 测试题目解析
        result = service.explain_question(
            question="小明有5个苹果，吃了2个，还剩几个？",
            user_answer="3",
            correct_answer="3",
            subject="math"
        )
        print("\n=== AI解析结果 ===")
        print(result)
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
