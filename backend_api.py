import json
import os
from flask import Flask, request, jsonify, stream_with_context, Response
from flask_cors import CORS
from openai import OpenAI
import uuid
import threading
from werkzeug.utils import secure_filename
import docx
import PyPDF2
from io import BytesIO
import time
from concurrent.futures import ThreadPoolExecutor
from enum import Enum

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 配置
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB 文件大小限制
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'doc', 'md'}

# 创建上传目录
upload_folder = os.path.join(os.path.dirname(__file__), 'uploads')
if not os.path.exists(upload_folder):
    os.makedirs(upload_folder)

# 任务状态枚举
class TaskStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

# 全局任务管理器
class TaskManager:
    def __init__(self):
        self.tasks = {}
        self.lock = threading.Lock()
        self.executor = ThreadPoolExecutor(max_workers=3)  # 限制并发任务数
    
    def create_task(self, task_id, task_type, **kwargs):
        """创建新任务"""
        with self.lock:
            self.tasks[task_id] = {
                'id': task_id,
                'type': task_type,
                'status': TaskStatus.PENDING,
                'progress': 0,
                'result': None,
                'error': None,
                'created_at': time.time(),
                'updated_at': time.time(),
                **kwargs
            }
        return task_id
    
    def update_task(self, task_id, **updates):
        """更新任务状态"""
        with self.lock:
            if task_id in self.tasks:
                self.tasks[task_id].update(updates)
                self.tasks[task_id]['updated_at'] = time.time()
    
    def get_task(self, task_id):
        """获取任务信息"""
        with self.lock:
            return self.tasks.get(task_id, None)
    
    def submit_task(self, task_id, func, *args, **kwargs):
        """提交异步任务"""
        def task_wrapper():
            try:
                self.update_task(task_id, status=TaskStatus.PROCESSING, progress=10)
                result = func(*args, **kwargs)
                self.update_task(task_id, 
                               status=TaskStatus.COMPLETED, 
                               progress=100, 
                               result=result)
                return result
            except Exception as e:
                self.update_task(task_id, 
                               status=TaskStatus.FAILED, 
                               progress=0, 
                               error=str(e))
                raise e
        
        future = self.executor.submit(task_wrapper)
        return future

# 创建全局任务管理器
task_manager = TaskManager()

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_file(file_path, filename):
    """从不同类型的文件中提取文本内容"""
    file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    
    try:
        if file_ext == 'txt' or file_ext == 'md':
            # 文本文件
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        elif file_ext == 'docx':
            # Word文档
            doc = docx.Document(file_path)
            text = []
            for paragraph in doc.paragraphs:
                text.append(paragraph.text)
            return '\n'.join(text)
        elif file_ext == 'pdf':
            # PDF文件
            text = []
            with open(file_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                for page in pdf_reader.pages:
                    text.append(page.extract_text())
            return '\n'.join(text)
        else:
            return None
    except Exception as e:
        print(f"提取文件内容失败: {str(e)}")
        return None

# 初始化学习导师agent
class CurriculumDrivenLearningTutor:
    def __init__(self, api_key, base_url, model_name='qwen-turbo'):
        """
        初始化学习导师agent
        :param api_key: 阿里云百炼API密钥
        :param base_url: API基础URL
        :param model_name: 使用的模型名称
        """
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self.model_name = model_name
        self.conversations = {}  # 存储所有对话历史
        self.conversations_file = os.path.join(os.path.dirname(__file__), 'conversations.json')
        self.lock = threading.Lock()  # 添加线程锁
        self.load_conversations()
        
    def create_conversation(self):
        """
        创建新对话
        :return: 对话ID
        """
        with self.lock:
            conversation_id = str(uuid.uuid4())
            self.conversations[conversation_id] = []
            self.save_conversations()
            return conversation_id
        
    def start_conversation(self, conversation_id, user_input):
        """
        开始对话
        :param conversation_id: 对话ID
        :param user_input: 用户输入
        :return: 模型回复
        """
        with self.lock:
            # 获取或创建对话历史
            if conversation_id not in self.conversations:
                self.conversations[conversation_id] = []
                
            # 添加用户输入到历史记录
            self.conversations[conversation_id].append({'role': 'user', 'content': user_input})
            
            # 构建系统提示
            system_prompt = self._build_system_prompt()
            
            # 准备消息列表
            messages = [{'role': 'system', 'content': system_prompt}] + self.conversations[conversation_id]
        
        # 调用模型
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=0.7,
                stream=True  # 启用流式输出
            )
            
            # 返回流式响应
            return response
        except Exception as e:
            return f"调用模型失败: {str(e)}"
    
    def add_assistant_message(self, conversation_id, content):
        """添加助手回复到对话历史"""
        with self.lock:
            if conversation_id in self.conversations:
                self.conversations[conversation_id].append({
                    'role': 'assistant',
                    'content': content
                })
                self.save_conversations()
    
    def save_conversations(self):
        """保存对话历史到文件"""
        try:
            with open(self.conversations_file, 'w', encoding='utf-8') as f:
                json.dump(self.conversations, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存对话历史失败: {str(e)}")

    def load_conversations(self):
        """从文件加载对话历史"""
        try:
            if os.path.exists(self.conversations_file):
                with open(self.conversations_file, 'r', encoding='utf-8') as f:
                    self.conversations = json.load(f)
            else:
                self.conversations = {}
        except Exception as e:
            print(f"加载对话历史失败: {str(e)}")
            self.conversations = {}
    
    def _build_system_prompt(self):
        """
        构建系统提示词
        """
        system_prompt = """# Role: 课程主导型学习导师 (Curriculum-Driven Learning Tutor)

## Profile:
- Author: Qwen
- Version: 1.0
- Language: 中文
- Description: 你是一位经验丰富的教学设计师和课程导师，专精于辅导学员备考各类专业资格认证考试。你的任务是接收我提供的《XX考试科目名称》完整学习材料，将其分解为一系列符合考试大纲的知识单元，然后以"提问-引导-讲解-答疑"的循环模式，一步步主动地带领我完成整个学习过程。你主导着学习的节奏和流程。

## Core Skills:
- **课程规划 (Lesson Planning)**: 你能快速分析《XX考试科目名称》教材，并根据考试大纲要求和内容的内在逻辑（如总分结构、递进关系、并列关系）将其智能地分解为多个适合单次学习的【知识单元】。
- **引导式提问 (Guided Questioning)**: 针对每个【知识单元】，你能设计出精准的、贴合考试考点的问题，并明确指出答案在原文中的大致位置，引导我主动阅读和发现。
- **知识重构与修正 (Knowledge Reframing & Correction)**: 你能在我回答后，提供一个超可读的、无痕修正原文错误的、并融合了图表引导的深度讲解。讲解中应特别强调考试的重点、难点和常考点。
- **会话管理 (Session Management)**: 你能清晰地管理学习流程的每一个状态，知道何时提问、何时等待、何时讲解、何时答疑，以及何时进入下一个【知识单元】。

## Master Workflow (你必须严格遵守的教学流程):

**Phase 0: 课程初始化 (Initialization & Planning)**
1. **接收材料**: 我会首先提供【书本全文】。
2. **内部规划**: 你需要立即对全文进行分析，将其切分为多个逻辑上的【知识单元】。切分应以考试大纲为主要依据，例如：
   - 单元1: [基础知识单元]
   - 单元2: [应用技能单元] 
   - 单元3: [案例分析单元]
3. **公布学习议程**: 你的第一个回复必须是向我展示这份学习计划。格式如下：
"你好！我是你的[考试科目名称]学习导师。我已经为您规划好了备考学习路径，我们将依次学习以下内容：
1. [知识单元1的标题]
2. [知识单元2的标题]
3. ...
准备好后，请告诉我，我们随时可以从第一个话题开始。"
然后等待我的确认。

**Phase 1: 学习循环 (The Learning Loop)**
这个阶段将针对每一个【知识单元】重复进行，直到所有单元学习完毕。

1. **发起单元学习**: 在我确认后，或者每当一个旧单元的答疑结束后，你将开启新单元的学习。你会说：
"好的，我们现在开始学习‘[当前知识单元的标题]’。"

2. **提问与定位**: 紧接着，你必须提出一个针对性问题，并为我定位。格式为：
"我的问题是：[针对当前单元的考试考点问题]？请阅读你原文的[如：第一章第一节]，尝试找到答案并告诉我。"

然后，你会停止并等待我的回答。

3. **等待用户回答**: 你在此步骤中，除了等待，不做任何事。

4. **讲解与答疑环节**: 在我回答之后，你将：
   a. **肯定与过渡**: 以"非常好！你已经找到了关键考点！"或"回答得很接近了，但我们可以再深入一点。"开始。
   b. **进行深度讲解**: 提供你最擅长的"超可读性讲解"，在此过程中【无痕修正】原文错误，并适时插入【图表引导】（例如："关于这一点，你可以对照书中的[图表名称]来看，会更清晰。"）。讲解时需突出该知识点在考试中的重要性、可能出现的题型（如单选、多选、案例分析）以及与其他考点的关联。
   c. **开启答疑模式**: 讲解结束后，你必须主动、清晰地询问：
"关于‘[当前知识单元的标题]’这个知识点，你还有其他疑问吗？请随时提出，我会一直为你解答，直到你完全理解为止。"

5. **循环退出条件**: 你会持续回答我对当前知识点的疑问。只有当我明确表示"没有问题了"、"我懂了"、"继续吧"或类似意思时，你才会结束当前单元的答疑。

6. **单元总结与推进**: 在退出答疑后，进行单元总结，回顾考试要点和难点。总结完毕后，你会询问：
"[总结内容]...这个单元我们已经掌握了，准备好开始下一个了吗？"
然后等待我的确认。如果所有单元都已完成，则进入Phase 2。

**Phase 2: 课程结束 (Conclusion)**
1. **总结**: 当所有【知识单元】学习完毕后，你将对我进行一个最后的简短总结，回顾我们学过的所有章节的主要内容。
2. **鼓励**: 最后给予我鼓励，例如："恭喜你完成了本次学习！坚持下去，胜利就在眼前！"

请严格按照以上角色设定和工作流程与用户交互。"""
        
        return system_prompt

# 从环境变量获取API配置
def get_api_config():
    """从环境变量获取API配置"""
    api_key = os.getenv('DASHSCOPE_API_KEY', 'sk-9abb3f33c72440f488d9b470ab701d39')  # 默认值仅用于开发
    base_url = os.getenv('DASHSCOPE_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
    model_name = os.getenv('MODEL_NAME', 'qwen3-30b-a3b-instruct-2507')
    return api_key, base_url, model_name

# 创建学习导师实例
api_key, base_url, model_name = get_api_config()
tutor = CurriculumDrivenLearningTutor(
    api_key=api_key,
    base_url=base_url,
    model_name=model_name
)

@app.route('/api/new-conversation', methods=['POST'])
def new_conversation():
    """
    创建新对话
    """
    conversation_id = tutor.create_conversation()
    return jsonify({
        'conversation_id': conversation_id,
        'message': '新对话已创建'
    })

@app.route('/api/chat', methods=['POST'])
def chat():
    """
    处理聊天消息
    """
    data = request.json
    conversation_id = data.get('conversation_id')
    user_message = data.get('message')
    
    if not conversation_id or not user_message:
        return jsonify({'error': '缺少必要参数'}), 400
    
    # 使用流式响应返回结果
    def generate():
        response = tutor.start_conversation(conversation_id, user_message)
        if isinstance(response, str):  # 错误消息
            yield f"data: {json.dumps({'error': response})}\n\n"
            return
            
        # 流式输出模型回复
        full_response = ""
        for chunk in response:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                full_response += content
                yield f"data: {json.dumps({'content': content})}\n\n"
        
        # 将完整回复添加到对话历史
        tutor.conversations[conversation_id].append({
            'role': 'assistant',
            'content': full_response
        })
        tutor.save_conversations()
        yield f"data: {json.dumps({'done': True})}\n\n"
    
    return Response(stream_with_context(generate()), content_type='text/event-stream')

def analyze_file_content_async(task_id, conversation_id, file_content):
    """异步分析文件内容"""
    try:
        # 更新进度：开始分析
        task_manager.update_task(task_id, progress=30, status=TaskStatus.PROCESSING)
        
        # 添加用户消息到对话历史
        with tutor.lock:
            tutor.conversations[conversation_id].append({
                'role': 'user', 
                'content': f'请分析以下教材内容:\n\n{file_content}'
            })
        
        # 更新进度：准备调用AI
        task_manager.update_task(task_id, progress=50)
        
        # 构建系统提示
        system_prompt = tutor._build_system_prompt()
        
        # 准备消息列表
        messages = [{'role': 'system', 'content': system_prompt}] + tutor.conversations[conversation_id]
        
        # 更新进度：调用AI模型
        task_manager.update_task(task_id, progress=70)
        
        # 调用模型
        response = tutor.client.chat.completions.create(
            model=tutor.model_name,
            messages=messages,
            temperature=0.7,
            stream=False
        )
        
        # 获取AI回复
        ai_response = response.choices[0].message.content
        
        # 更新进度：保存结果
        task_manager.update_task(task_id, progress=90)
        
        # 添加AI回复到对话历史
        tutor.add_assistant_message(conversation_id, ai_response)
        
        return {
            'conversation_id': conversation_id,
            'ai_response': ai_response
        }
        
    except Exception as e:
        print(f"异步分析文件内容失败: {str(e)}")
        raise e

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """
    文件上传接口 - 异步处理版本
    """
    try:
        if 'file' not in request.files:
            return jsonify({'error': '没有文件'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '没有选择文件'}), 400
        
        # 检查文件类型
        if not allowed_file(file.filename):
            return jsonify({'error': f'不支持的文件类型。支持的类型: {", ".join(ALLOWED_EXTENSIONS)}'}), 400
        
        # 安全的文件名
        secure_name = secure_filename(file.filename)
        filename = f"{uuid.uuid4()}_{secure_name}"
        file_path = os.path.join(upload_folder, filename)
        
        # 保存文件
        file.save(file_path)
        
        # 提取文件内容
        file_content = extract_text_from_file(file_path, file.filename)
        
        # 创建新对话
        conversation_id = tutor.create_conversation()
        
        # 创建分析任务
        task_id = str(uuid.uuid4())
        
        # 如果成功提取到文件内容，启动异步分析
        if file_content and file_content.strip():
            # 创建任务
            task_manager.create_task(
                task_id=task_id,
                task_type='file_analysis',
                filename=filename,
                conversation_id=conversation_id,
                file_size=os.path.getsize(file_path)
            )
            
            # 提交异步任务
            task_manager.submit_task(
                task_id,
                analyze_file_content_async,
                task_id,
                conversation_id,
                file_content
            )
            
            return jsonify({
                'message': '文件上传成功，正在分析中',
                'filename': filename,
                'size': os.path.getsize(file_path),
                'path': file_path,
                'content_preview': file_content[:500] + '...' if len(file_content) > 500 else file_content,
                'conversation_id': conversation_id,
                'task_id': task_id,
                'has_content': True,
                'status': 'processing'
            })
        else:
            return jsonify({
                'message': '文件上传成功，但未能提取到文本内容',
                'filename': filename,
                'size': os.path.getsize(file_path),
                'path': file_path,
                'conversation_id': conversation_id,
                'has_content': False,
                'status': 'completed'
            })
        
    except Exception as e:
        return jsonify({'error': f'文件上传失败: {str(e)}'}), 500

@app.route('/api/task/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """
    获取任务状态
    """
    task = task_manager.get_task(task_id)
    if not task:
        return jsonify({'error': '任务不存在'}), 404
    
    # 转换枚举为字符串
    task_info = dict(task)
    task_info['status'] = task['status'].value
    
    return jsonify(task_info)

@app.route('/api/analyze-stream/<conversation_id>', methods=['GET'])
def stream_analysis_result(conversation_id):
    """
    流式获取分析结果
    """
    def generate():
        # 检查对话是否存在
        if conversation_id not in tutor.conversations:
            yield f"data: {json.dumps({'error': '对话不存在'})}\n\n"
            return
        
        # 获取最新的助手回复
        messages = tutor.conversations[conversation_id]
        if not messages:
            yield f"data: {json.dumps({'error': '暂无分析结果'})}\n\n"
            return
        
        # 找到最后一条助手消息
        last_assistant_message = None
        for msg in reversed(messages):
            if msg['role'] == 'assistant':
                last_assistant_message = msg
                break
        
        if not last_assistant_message:
            yield f"data: {json.dumps({'error': '暂无AI回复'})}\n\n"
            return
        
        # 模拟流式输出已有的回复
        content = last_assistant_message['content']
        chunk_size = 50  # 每次发送50个字符
        
        for i in range(0, len(content), chunk_size):
            chunk = content[i:i + chunk_size]
            yield f"data: {json.dumps({'content': chunk})}\n\n"
            time.sleep(0.1)  # 模拟流式延迟
        
        yield f"data: {json.dumps({'done': True})}\n\n"
    
    return Response(stream_with_context(generate()), content_type='text/event-stream')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
