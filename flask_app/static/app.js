/**
 * 小学刷题乐园 - 前端应用逻辑
 * 调用后端 API 实现前后端分离
 * 依赖：config.js（先加载）
 */

const DEFAULT_AVATAR = 'images/default-avatar.webp';

// ============== 认证相关 ==============

/**
 * 获取认证 Token
 */
function getAuthToken() {
    return localStorage.getItem('authToken');
}

/**
 * 获取当前用户 ID
 */
function getCurrentUserId() {
    return localStorage.getItem('userId');
}

/**
 * 检查是否已登录
 */
function isLoggedIn() {
    return !!getAuthToken();
}

/**
 * 显示登录提示弹窗
 */
function showLoginRequiredModal(returnUrl) {
    // 如果已经登录，直接返回
    if (isLoggedIn()) {
        return;
    }
    
    // 保存当前页面 URL，用于登录后返回
    if (!returnUrl) {
        returnUrl = window.location.href;
    }
    localStorage.setItem('loginReturnUrl', returnUrl);
    
    // 创建弹窗 HTML
    const modalHTML = `
        <div class="modal login-required-modal" id="login-required-modal">
            <div class="modal-content">
                <div class="modal-body" style="padding: 40px 32px;">
                    <div class="login-required-icon">🎓</div>
                    <div class="login-required-title">登录解锁更多功能，记录你的学习成长！</div>
                    <div class="login-required-desc">
                        登录后可以保存学习进度、查看排行榜、解锁成就，让学习更有动力！
                    </div>
                    <div class="login-benefits">
                        <div class="login-benefit-item">
                            <span class="login-benefit-icon">📊</span>
                            <span>保存答题记录和学习进度</span>
                        </div>
                        <div class="login-benefit-item">
                            <span class="login-benefit-icon">🏆</span>
                            <span>查看排行榜，和同学一起竞争</span>
                        </div>
                        <div class="login-benefit-item">
                            <span class="login-benefit-icon">⭐</span>
                            <span>解锁成就，获得专属徽章</span>
                        </div>
                        <div class="login-benefit-item">
                            <span class="login-benefit-icon">📝</span>
                            <span>错题本自动记录，针对性复习</span>
                        </div>
                    </div>
                </div>
                <div class="modal-footer modal-footer-center">
                    <button class="btn-login-secondary" onclick="closeLoginModal()">稍后再说</button>
                    <button class="btn-login-primary" onclick="goToLogin()">立即登录</button>
                </div>
            </div>
        </div>
    `;
    
    // 添加到页面
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    
    // 阻止背景滚动
    document.body.style.overflow = 'hidden';
}

/**
 * 关闭登录提示弹窗
 */
function closeLoginModal() {
    const modal = document.getElementById('login-required-modal');
    if (modal) {
        modal.remove();
        document.body.style.overflow = '';
    }
}

/**
 * 跳转到登录页
 */
function goToLogin() {
    const returnUrl = localStorage.getItem('loginReturnUrl') || window.location.href;
    window.location.href = `login.html?return=${encodeURIComponent(returnUrl)}`;
}

/**
 * 更新登录状态显示
 */
function updateLoginStatus() {
    const statusDiv = document.getElementById('login-status');
    const welcomeText = document.getElementById('welcome-text');
    const logoutBtn = document.getElementById('logout-btn');
    
    const username = localStorage.getItem('username');
    const studentName = localStorage.getItem('studentName');
    const isLoggedIn = !!username;
    
    // 显示欢迎文本（用户名/昵称）
    if (welcomeText) {
        if (username) {
            welcomeText.textContent = `👋 欢迎，${studentName || username}！`;
        } else {
            welcomeText.textContent = '👋 欢迎来到刷题乐园';
        }
    }
    
    // 显示登录状态
    if (statusDiv) {
        if (username) {
            statusDiv.textContent = `✅ 已登录：${username}`;
            statusDiv.style.color = '#4caf50';
        } else {
            statusDiv.textContent = '❌ 未登录';
            statusDiv.style.color = '#f44336';
        }
    }
    
    // 控制退出按钮显示（仅登录时显示）
    if (logoutBtn) {
        logoutBtn.style.display = isLoggedIn ? 'block' : 'none';
    }
}

// ============== 应用状态 ==============
let appState = {
    userId: null,
    currentSubject: null,
    currentLevel: 1,
    currentQuestionIndex: 0,
    questions: [],
    userAnswers: [],
    timer: null,
    seconds: 0,
    quizStartTime: null,  // 当前题目开始时间
    stats: {
        totalQuestions: 0,
        correctCount: 0,
        perfectScore: 0,
        consecutiveDays: 0,
        wrongBookCleared: 0  // 清空错题本次数
    },
    wrongBook: [],
    achievements: [],
    practicedSubjects: new Set()  // 练习过的科目
};

// ============== 初始化 ==============

/**
 * 初始化应用
 */
async function initApp() {
    console.log('🚀 应用初始化中...');
    
    // 检查健康状态
    try {
        const health = await apiRequest('/health');
        console.log('✓ 后端服务连接成功:', health.message);
    } catch (error) {
        console.error('❌ 后端服务未启动，请确保 Flask 服务正在运行');
        alert('后端服务未启动，请稍后再试！');
        return;
    }
    
    // 更新登录状态显示
    updateLoginStatus();
    
    // 加载或创建用户
    await loadOrCreateUser();
    
    // 加载头像（在首页和个人中心都显示）
    loadAvatar();
    
    // 加载成就列表
    await loadAchievements();
    
    // 更新界面
    updateStatsDisplay();
    await updateAchievements();  // 加载已解锁的成就
    
    // 加载每日任务（如果在首页）
    if (document.getElementById('daily-task-card')) {
        await loadDailyTask();
    }
    
    console.log('✓ 应用初始化完成');
}

/**
 * 加载或创建用户
 */
async function loadOrCreateUser() {
    // 优先使用认证系统的用户 ID
    let userId = getCurrentUserId();
    
    // 如果没有，尝试旧的存储方式
    if (!userId) {
        userId = localStorage.getItem('quizUserId');
    }
    
    if (userId) {
        // 获取用户信息
        try {
            console.log('🔍 尝试加载用户信息, userId:', userId);
            const user = await apiRequest(`/user/${userId}`);
            console.log('✅ 成功获取用户信息:', user);
            appState.userId = user.id;
            appState.stats = user.stats;
            
            // 保存username到localStorage（关键修复）
            if (!localStorage.getItem('username') && user.username) {
                localStorage.setItem('username', user.username);
            }
            
            // 优先使用登录时的用户名，其次使用存储的昵称
            const savedName = localStorage.getItem('studentName');
            const displayName = savedName || user.student_name || user.username || '新学生';
            
            // 更新显示名称（兼容不同页面的元素ID）
            const nameElement = document.getElementById('student-name') || 
                               document.getElementById('profile-student-name');
            if (nameElement) {
                nameElement.textContent = displayName;
            }
            
            // 更新等级显示（兼容不同页面的元素ID）
            const levelElement = document.getElementById('student-level') || 
                                document.getElementById('profile-level') ||
                                document.getElementById('profile-student-level');
            if (levelElement) {
                levelElement.textContent = user.level;
            }
            
            // 同步服务器头像
            if (user.avatar) {
                localStorage.setItem('userAvatar', user.avatar);
            } else {
                localStorage.removeItem('userAvatar');
            }
            
            // 更新登录状态显示（确保显示用户名）
            if (!localStorage.getItem('studentName')) {
                localStorage.setItem('studentName', displayName);
            }
            updateLoginStatus();
            
            // 加载错题本
            await loadWrongBook();
            
            console.log('✓ 用户信息加载成功:', displayName, '用户名:', localStorage.getItem('username'));
        } catch (error) {
            console.error('❌ 用户信息加载失败:', error.message || error);
            console.error('   userId:', userId);
            console.error('   localStorage中的userId:', localStorage.getItem('userId'));
            console.error('   localStorage中的username:', localStorage.getItem('username'));
            console.warn('⚠️ 将创建新用户');
            await createNewUser();
        }
    } else {
        // 创建新用户
        await createNewUser();
    }
}

/**
 * 创建新用户
 */
async function createNewUser() {
    // 安全地获取student-name元素
    const nameElement = document.getElementById('student-name');
    let studentName = '新学生';
    
    if (nameElement) {
        studentName = nameElement.textContent || '新学生';
    } else {
        // 如果页面上没有student-name元素，从 localStorage获取
        studentName = localStorage.getItem('studentName') || '新学生';
    }
    
    try {
        const response = await apiRequest('/user/create', 'POST', { student_name: studentName });
        appState.userId = response.user_id;
        // 同时保存两个key，保持兼容性
        localStorage.setItem('userId', response.user_id);
        localStorage.setItem('quizUserId', response.user_id);
        
        console.log('✓ 新用户创建成功，ID:', response.user_id);
    } catch (error) {
        console.error('创建用户失败:', error);
    }
}

/**
 * 加载成就列表
 */
async function loadAchievements() {
    try {
        const response = await apiRequest('/achievements');
        appState.achievements = response.achievements;
    } catch (error) {
        console.error('加载成就失败:', error);
    }
}

/**
 * 加载错题本
 */
function escapeHtml(text) {
    if (text == null) return '';
    return String(text)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

async function loadWrongBook() {
    const userId = appState.userId || getCurrentUserId() || localStorage.getItem('quizUserId');
    if (!userId) {
        console.log('用户未登录，无法加载错题本');
        const wrongBookList = document.getElementById('wrong-book-list');
        if (wrongBookList) {
            wrongBookList.innerHTML = '<p style="text-align:center;color:#999;padding:40px;">请先登录后查看错题本</p>';
        }
        return;
    }
    if (!appState.userId) {
        appState.userId = parseInt(userId, 10);
    }
    
    const wrongBookList = document.getElementById('wrong-book-list');
    if (wrongBookList) {
        wrongBookList.innerHTML = '<p style="text-align:center;color:#999;padding:40px;">加载中...</p>';
    }
    
    console.log('开始加载错题本，用户ID:', appState.userId);
    
    try {
        const response = await apiRequest(`/user/${appState.userId}/wrong-book`);
        console.log('API返回数据:', response);
        appState.wrongBook = response.wrong_book;
        console.log('错题数据已加载，数量:', appState.wrongBook ? appState.wrongBook.length : 0);
        renderWrongBook(); // 加载后渲染
        initWrongBookFilters(); // 初始化筛选器
    } catch (error) {
        console.error('加载错题本失败:', error);
        // 显示错误提示
        const wrongBookList = document.getElementById('wrong-book-list');
        if (wrongBookList) {
            wrongBookList.innerHTML = '<p style="text-align: center; color: #999; padding: 40px;">加载失败，请刷新重试</p>';
        }
    }
}

let wrongBookFiltersInitialized = false;

/**
 * 初始化错题本筛选器
 */
function initWrongBookFilters() {
    const filterButtons = document.querySelectorAll('#wrong-filters .filter-btn');
    if (!filterButtons.length) return;
    
    if (wrongBookFiltersInitialized) return;
    wrongBookFiltersInitialized = true;
    
    filterButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            // 移除所有按钮的 active 类
            filterButtons.forEach(b => b.classList.remove('active'));
            // 给当前按钮添加 active 类
            this.classList.add('active');
            // 获取筛选科目
            const subject = this.dataset.subject;
            // 重新渲染错题列表
            renderWrongBook(subject);
        });
    });
    
    // 添加刷新按钮事件
    const refreshBtn = document.getElementById('refresh-wrong-btn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', async function() {
            // 显示加载状态
            const originalText = this.innerHTML;
            this.innerHTML = '⏳ 刷新中...';
            this.disabled = true;
            
            try {
                // 重新加载数据
                await loadWrongBook();
                
                // 获取当前选中的筛选项
                const activeFilter = document.querySelector('.filter-btn.active');
                const currentSubject = activeFilter ? activeFilter.dataset.subject : 'all';
                
                // 重新渲染
                renderWrongBook(currentSubject);
                
                // 显示成功提示
                this.innerHTML = '✅ 已刷新';
                setTimeout(() => {
                    this.innerHTML = originalText;
                    this.disabled = false;
                }, 1500);
            } catch (error) {
                console.error('刷新失败:', error);
                this.innerHTML = '❌ 刷新失败';
                setTimeout(() => {
                    this.innerHTML = originalText;
                    this.disabled = false;
                }, 2000);
            }
        });
    }
}

/**
 * 渲染错题本
 */
function renderWrongBook(filterSubject = 'all') {
    const wrongBookList = document.getElementById('wrong-book-list');
    if (!wrongBookList) {
        console.warn('未找到 wrong-book-list 元素');
        return;
    }
    
    console.log('渲染错题本，当前错题数量:', appState.wrongBook ? appState.wrongBook.length : 0);
    console.log('筛选条件:', filterSubject);
    
    const clearBtn = document.getElementById('clear-wrong-btn');
    if (clearBtn) clearBtn.style.display = 'none';
    
    if (!appState.wrongBook || appState.wrongBook.length === 0) {
        console.log('没有错题数据，显示空状态');
        wrongBookList.innerHTML = `
            <div style="text-align: center; padding: 60px 20px;">
                <div style="font-size: 64px; margin-bottom: 20px;">📝</div>
                <h3 style="color: #666; margin-bottom: 10px;">暂无错题</h3>
                <p style="color: #999;">太棒了！你还没有答错过题目</p>
            </div>
        `;
        return;
    }
    
    // 科目名称映射
    const subjectNames = {
        'math': '数学',
        'chinese': '语文',
        'english': '英语',
        'science': '科学',
        'history': '历史'
    };
    
    // 根据筛选条件过滤错题
    let filteredWrongs = appState.wrongBook;
    if (filterSubject !== 'all') {
        filteredWrongs = appState.wrongBook.filter(item => item.subject === filterSubject);
    }
    
    if (filteredWrongs.length === 0) {
        if (clearBtn) clearBtn.style.display = appState.wrongBook.length > 0 ? 'block' : 'none';
        wrongBookList.innerHTML = `
            <div style="text-align: center; padding: 60px 20px;">
                <div style="font-size: 64px; margin-bottom: 20px;">🔍</div>
                <h3 style="color: #666; margin-bottom: 10px;">该科目暂无错题</h3>
                <p style="color: #999;">继续加油，保持好成绩！</p>
            </div>
        `;
        return;
    }
    
    let html = '';
    filteredWrongs.forEach((item) => {
        const subjectName = subjectNames[item.subject] || item.subject;
        const date = item.last_wrong_at
            ? new Date(item.last_wrong_at).toLocaleDateString('zh-CN')
            : '未知日期';
        
        html += `
            <div class="wrong-item">
                <div class="wrong-item-header">
                    <span class="wrong-subject">${escapeHtml(subjectName)}</span>
                    <span style="color: #999; font-size: 14px;">错误 ${item.wrong_count || 1} 次 · ${escapeHtml(date)}</span>
                    <button type="button" class="ai-explain-btn" onclick="explainWithAI(${item.id}, this)">🤖 AI解析</button>
                </div>
                <div class="wrong-question">${escapeHtml(item.question || '（题目内容缺失）')}</div>
                <div class="wrong-answer">❌ 你的答案：${escapeHtml(item.user_answer || '未作答')}</div>
                <div class="wrong-correct">✅ 正确答案：${escapeHtml(item.correct_answer || '未知')}</div>
                <div class="ai-explanation-content" id="ai-explanation-${item.id}"></div>
            </div>
        `;
    });
    
    console.log('生成的HTML长度:', html.length);
    console.log('准备设置innerHTML...');
    wrongBookList.innerHTML = html;
    if (clearBtn) clearBtn.style.display = 'block';
    
    console.log('innerHTML设置完成，子元素数量:', wrongBookList.children.length);
    
    // 调试：检查第一个子元素
    if (wrongBookList.children.length > 0) {
        console.log('第一个子元素:', wrongBookList.children[0]);
        console.log('第一个子元素的class:', wrongBookList.children[0].className);
        const computedStyle = window.getComputedStyle(wrongBookList.children[0]);
        console.log('display:', computedStyle.display);
        console.log('visibility:', computedStyle.visibility);
        console.log('opacity:', computedStyle.opacity);
    }
}

// ============== API 请求封装 ==============

/**
 * 发送 API 请求
 */
async function apiRequest(endpoint, method = 'GET', data = null) {
    const url = `${API_BASE_URL}${endpoint}`;
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json'
        }
    };
    
    // 添加认证 Token
    const token = getAuthToken();
    if (token) {
        options.headers['Authorization'] = `Bearer ${token}`;
    }
    
    if (data && (method === 'POST' || method === 'PUT')) {
        options.body = JSON.stringify(data);
    }
    
    const response = await fetch(url, options);
    
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
}

// ============== 用户界面交互 ==============

/**
 * 更新统计显示
 */
function updateStatsDisplay() {
    // 安全地更新统计元素（仅在元素存在时更新）
    const totalEl = document.getElementById('total-questions');
    const correctEl = document.getElementById('correct-count');
    const accuracyEl = document.getElementById('accuracy-rate');
    
    if (totalEl) {
        totalEl.textContent = appState.stats.totalQuestions;
    }
    if (correctEl) {
        correctEl.textContent = appState.stats.correctCount;
    }
    if (accuracyEl) {
        const accuracy = appState.stats.totalQuestions > 0 
            ? Math.round((appState.stats.correctCount / appState.stats.totalQuestions) * 100) 
            : 0;
        accuracyEl.textContent = accuracy + '%';
    }
}

/**
 * 更新用户数据到后端
 */
async function updateUserStats() {
    if (!appState.userId) return;
    
    try {
        await apiRequest(`/user/${appState.userId}/update`, 'POST', {
            total_questions: appState.stats.totalQuestions,
            correct_count: appState.stats.correctCount,
            perfect_score: appState.stats.perfectScore,
            consecutive_days: appState.stats.consecutiveDays
        });
    } catch (error) {
        console.error('更新用户数据失败:', error);
    }
}

/**
 * 选择科目
 */
function selectSubject(subject) {
    appState.currentSubject = subject;
    
    // 记录练习过的科目（用于成就"科目精通"）
    appState.practicedSubjects.add(subject);
    
    // 跳转到关卡选择页
    window.location.href = `level.html?subject=${subject}`;
    
    console.log(`✓ 选择科目：${subject}，已练习科目：`, Array.from(appState.practicedSubjects));
}

/**
 * 初始化关卡选择页面
 */
async function initLevelPage() {
    // 从URL获取科目
    const urlParams = new URLSearchParams(window.location.search);
    const subject = urlParams.get('subject') || 'math';
    
    // 更新页面标题
    const subjectNames = {
        'math': '数学',
        'chinese': '语文',
        'english': '英语',
        'science': '科学',
        'history': '历史'
    };
    
    const subjectTitle = document.getElementById('subject-title');
    if (subjectTitle) {
        subjectTitle.textContent = `${subjectNames[subject] || '数学'} - 选择年级`;
    }
    
    // 高亮当前科目的菜单项
    const menuItems = document.querySelectorAll('.menu-item[data-subject]');
    menuItems.forEach(item => {
        if (item.dataset.subject === subject) {
            item.classList.add('active');
        } else {
            item.classList.remove('active');
        }
    });
    
    // 生成关卡卡片
    const levelGrid = document.getElementById('level-grid');
    if (!levelGrid) return;
    
    levelGrid.innerHTML = '';
    
    try {
        // 从后端获取该科目的年级信息
        const response = await apiRequest('/subjects');
        const subjects = response.subjects || {};
        const subjectData = subjects[subject];
        
        if (!subjectData) {
            levelGrid.innerHTML = '<p style="text-align:center; color:var(--text-secondary);">该科目暂无数据</p>';
            return;
        }
        
        const availableLevels = subjectData.levels || [];
        const levelCounts = subjectData.level_counts || {};
        const levelNames = ['一', '二', '三', '四', '五', '六'];
        
        // 根据数据库中的实际年级生成关卡
        for (const level of availableLevels) {
            const levelCard = document.createElement('a');
            levelCard.href = `quiz.html?subject=${subject}&level=${level}`;
            levelCard.className = 'level-card';
            
            const questionCount = levelCounts[level] || 0;
            
            levelCard.innerHTML = `
                <div class="level-number">${level}</div>
                <div class="level-name">${levelNames[level-1] || level}年级</div>
                <div class="level-info">${questionCount}道题目</div>
                <div class="level-stars" id="stars-${level}">☆☆☆</div>
            `;
            
            levelGrid.appendChild(levelCard);
        }
        
        // 加载用户在该科目的进度
        await loadLevelProgress(subject);
        
    } catch (error) {
        console.error('加载关卡失败:', error);
        levelGrid.innerHTML = '<p style="text-align:center; color:var(--text-secondary);">加载失败，请刷新重试</p>';
    }
}

/**
 * 加载关卡进度
 */
async function loadLevelProgress(subject) {
    try {
        const response = await apiRequest('/user-data');
        const progress = response.progress || {};
        const subjectProgress = progress[subject] || {};
        
        // 更新每个关卡的星级
        for (let i = 1; i <= 6; i++) {
            const starsElement = document.getElementById(`stars-${i}`);
            if (starsElement && subjectProgress[i]) {
                const stars = subjectProgress[i].stars || 0;
                starsElement.textContent = '★'.repeat(stars) + '☆'.repeat(3 - stars);
            }
        }
    } catch (error) {
        console.error('加载关卡进度失败:', error);
    }
}

/**
 * 开始关卡
 */
async function startLevel(level) {
    appState.currentLevel = level;
    appState.currentQuestionIndex = 0;
    appState.userAnswers = [];
    appState.seconds = 0;
    
    // 从后端获取题目
    try {
        const response = await apiRequest(`/questions?subject=${appState.currentSubject}&level=${level}`);
        appState.questions = response.questions;
        
        if (appState.questions.length === 0) {
            alert('该级别暂无题目，请选择其他级别！');
            return;
        }
        
        document.getElementById('total-questions-quiz').textContent = appState.questions.length;
        startTimer();
        showQuestion();
        
        console.log(`✓ 已加载 ${appState.questions.length} 道题目`);
    } catch (error) {
        console.error('获取题目失败:', error);
        alert('获取题目失败，请检查网络连接！');
    }
}

/**
 * 显示题目
 */
function showQuestion() {
    const question = appState.questions[appState.currentQuestionIndex];
    document.getElementById('current-question').textContent = appState.currentQuestionIndex + 1;
    document.getElementById('question-type').textContent = question.type === 'choice' ? '选择题' : '填空题';
    document.getElementById('question-text').textContent = question.question;
    
    // 更新进度条
    const progress = ((appState.currentQuestionIndex) / appState.questions.length) * 100;
    document.getElementById('progress-fill').style.width = progress + '%';
    
    // 隐藏反馈和下一题按钮
    document.getElementById('feedback').className = 'feedback';
    document.getElementById('feedback').style.display = 'none';
    document.getElementById('next-btn').style.display = 'none';
    const clickHint = document.getElementById('click-hint');
    if (clickHint) clickHint.style.display = 'block';
    
    // 生成选项或输入框
    const optionsContainer = document.getElementById('options-container');
    const inputContainer = document.getElementById('input-container');
    
    if (question.type === 'choice') {
        optionsContainer.style.display = 'flex';
        inputContainer.style.display = 'none';
        optionsContainer.innerHTML = '';
        
        question.options.forEach((option, index) => {
            const btn = document.createElement('button');
            btn.className = 'option-btn';
            btn.textContent = String.fromCharCode(65 + index) + '. ' + option;
            btn.onclick = () => selectOption(index, btn);
            btn.style.pointerEvents = 'auto';
            optionsContainer.appendChild(btn);
        });
    } else {
        optionsContainer.style.display = 'none';
        inputContainer.style.display = 'flex';
        document.getElementById('answer-input').value = '';
        document.getElementById('answer-input').focus();
    }
    
    selectedOption = null;
    
    // 记录题目开始时间
    appState.quizStartTime = Date.now();
}

/**
 * 选择选项
 */
let selectedOption = null;
function selectOption(index, btn) {
    if (document.getElementById('next-btn').style.display === 'block') {
        return;
    }
    selectedOption = index;
    submitAnswer();
}

/**
 * 提交答案
 */
async function submitAnswer() {
    const question = appState.questions[appState.currentQuestionIndex];
    let userAnswer;
    
    if (question.type === 'choice') {
        if (selectedOption === null) {
            alert('请先选择一个答案！');
            return;
        }
        userAnswer = question.options[selectedOption];
    } else {
        userAnswer = document.getElementById('answer-input').value.trim();
        if (!userAnswer) {
            alert('请输入答案！');
            return;
        }
    }
    
    const isCorrect = userAnswer === question.answer;
    
    appState.userAnswers.push({
        question: question,
        userAnswer: userAnswer,
        correct: isCorrect
    });
    
    // 提交答案到后端
    if (appState.userId) {
        try {
            // 计算答题用时（秒）
            let timeSpent = 0;
            if (appState.quizStartTime) {
                timeSpent = Math.floor((Date.now() - appState.quizStartTime) / 1000);
            }
            
            await apiRequest('/answer/submit', 'POST', {
                user_id: appState.userId,
                question_id: question.id,
                subject: appState.currentSubject,
                user_answer: userAnswer,
                is_correct: isCorrect,
                time_spent: timeSpent
            });
        } catch (error) {
            console.error('提交答案失败:', error);
        }
    }
    
    // 显示反馈
    const feedback = document.getElementById('feedback');
    if (isCorrect) {
        feedback.textContent = '🎉 答对了！真棒！';
        feedback.className = 'feedback correct';
        feedback.style.display = 'block';
        
        if (question.type === 'choice') {
            const buttons = document.querySelectorAll('.option-btn');
            buttons[selectedOption].classList.add('correct');
            buttons.forEach(btn => btn.style.pointerEvents = 'none');
        }
    } else {
        feedback.textContent = '💪 答错了，正确答案是：' + question.answer;
        feedback.className = 'feedback wrong';
        feedback.style.display = 'block';
        
        if (question.type === 'choice') {
            const buttons = document.querySelectorAll('.option-btn');
            buttons[selectedOption].classList.add('wrong');
            question.options.forEach((opt, idx) => {
                if (opt === question.answer) {
                    buttons[idx].classList.add('correct');
                }
            });
        }
        
        // 刷新错题本
        await loadWrongBook();
    }
    
    const clickHint = document.getElementById('click-hint');
    if (clickHint) clickHint.style.display = 'none';
    document.getElementById('next-btn').style.display = 'block';
    selectedOption = null;
    
    // 更新每日任务进度
    await updateDailyTaskProgress();
}

/**
 * 下一题
 */
function nextQuestion() {
    appState.currentQuestionIndex++;
    
    if (appState.currentQuestionIndex >= appState.questions.length) {
        finishQuiz();
    } else {
        showQuestion();
    }
}

/**
 * 开始计时器
 */
function startTimer() {
    appState.seconds = 0;
    document.getElementById('timer').textContent = '00:00';
    
    appState.timer = setInterval(() => {
        appState.seconds++;
        const mins = Math.floor(appState.seconds / 60).toString().padStart(2, '0');
        const secs = (appState.seconds % 60).toString().padStart(2, '0');
        document.getElementById('timer').textContent = mins + ':' + secs;
    }, 1000);
}

/**
 * 停止计时器
 */
function stopTimer() {
    if (appState.timer) {
        clearInterval(appState.timer);
        appState.timer = null;
    }
}

/**
 * 完成练习
 */
async function finishQuiz() {
    stopTimer();
    
    const correctCount = appState.userAnswers.filter(a => a.correct).length;
    const total = appState.questions.length;
    const score = Math.round((correctCount / total) * 100);
    
    // 更新统计
    appState.stats.totalQuestions += total;
    appState.stats.correctCount += correctCount;
    if (correctCount === total) {
        appState.stats.perfectScore++;
    }
    
    // 保存到后端
    await updateUserStats();
    
    // 检查并解锁成就（包括科目精通）
    await checkAchievements();
    
    // 保存结果到sessionStorage
    const mins = Math.floor(appState.seconds / 60).toString().padStart(2, '0');
    const secs = (appState.seconds % 60).toString().padStart(2, '0');
    
    sessionStorage.setItem('lastResult', JSON.stringify({
        score: score,
        correct: correctCount,
        wrong: total - correctCount,
        time: mins + ':' + secs
    }));
    
    // 跳转到结果页
    window.location.href = 'result.html';
}

/**
 * 显示成就提示
 */
function showAchievementToast(achievement) {
    const toast = document.getElementById('achievement-toast');
    const icon = document.getElementById('achievement-toast-icon');
    const name = document.getElementById('achievement-toast-name');
    const desc = document.getElementById('achievement-toast-desc');
    
    if (!toast || !achievement) return;
    
    // 设置内容
    icon.textContent = achievement.icon;
    name.textContent = achievement.name;
    desc.textContent = achievement.desc;
    
    // 显示提示
    toast.classList.add('show');
    
    // 播放提示音（可选）
    playAchievementSound();
    
    // 5 秒后隐藏
    setTimeout(() => {
        toast.classList.remove('show');
    }, 5000);
}

/**
 * 播放成就提示音
 */
function playAchievementSound() {
    // 使用 Web Audio API 播放简单的提示音
    try {
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);
        
        oscillator.frequency.value = 523.25; // C5
        oscillator.type = 'sine';
        
        gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);
        
        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 0.5);
    } catch (error) {
        console.log('提示音播放失败:', error);
    }
}

/**
 * 检查成就
 */
async function checkAchievements() {
    if (!appState.userId) return;
    
    const achievementsToUnlock = [];
    
    // 新手上路 - 完成第一次答题
    if (appState.stats.totalQuestions >= 1 && !hasAchievement(1)) achievementsToUnlock.push(1);
    // 初露锋芒 - 答对 10 道题
    if (appState.stats.correctCount >= 10 && !hasAchievement(2)) achievementsToUnlock.push(2);
    // 学习达人 - 累计答题 50 道
    if (appState.stats.totalQuestions >= 50 && !hasAchievement(3)) achievementsToUnlock.push(3);
    // 完美主义者 - 一次练习全对
    if (appState.stats.perfectScore >= 1 && !hasAchievement(4)) achievementsToUnlock.push(4);
    // 科目精通 - 三科都练习过
    if (appState.practicedSubjects && appState.practicedSubjects.size >= 3 && !hasAchievement(6)) achievementsToUnlock.push(6);
    // 错题克星 - 清空错题本
    if (appState.stats.wrongBookCleared >= 1 && !hasAchievement(7)) achievementsToUnlock.push(7);
    // 百题大师 - 累计答题 100 道
    if (appState.stats.totalQuestions >= 100 && !hasAchievement(8)) achievementsToUnlock.push(8);
    
    // 解锁成就
    for (const achievementId of achievementsToUnlock) {
        try {
            const response = await apiRequest(`/user/${appState.userId}/achievement/unlock`, 'POST', {
                achievement_id: achievementId
            });
            
            console.log(`✓ 解锁成就：${achievementId}`);
            
            // 如果是新解锁的成就，显示提示
            if (response.newly_unlocked && response.achievement) {
                showAchievementToast(response.achievement);
            }
        } catch (error) {
            console.error('解锁成就失败:', error);
        }
    }
}

/**
 * 检查是否已拥有成就
 */
function hasAchievement(id) {
    // 简单实现，实际应从后端获取
    return false;
}

/**
 * 查看错题
 */
function reviewWrong() {
    const wrongQuestions = appState.userAnswers.filter(a => !a.correct).map(a => a.question);
    if (wrongQuestions.length > 0) {
        alert('错题已保存到错题本，可以在首页查看哦！');
    }
    window.location.href = 'index.html';
}

/**
 * 返回首页
 */
function goHome() {
    window.location.href = 'index.html';
}

/**
 * 显示错题本（兼容旧调用）
 */
async function showWrongBook() {
    await loadWrongBook();
}

/**
 * 清空错题本
 */
async function clearWrongBook() {
    if (!appState.userId) return;
    
    if (confirm('确定要清空错题本吗？')) {
        try {
            await apiRequest(`/user/${appState.userId}/wrong-book/clear`, 'POST');
            appState.wrongBook = [];
            renderWrongBook('all');
            
            // 增加清空次数（用于成就“错题克星”）
            appState.stats.wrongBookCleared = (appState.stats.wrongBookCleared || 0) + 1;
            console.log('✓ 错题本已清空，清空次数:', appState.stats.wrongBookCleared);
            
            // 检查成就
            await checkAchievements();
        } catch (error) {
            console.error('清空错题本失败:', error);
        }
    }
}

/**
 * 显示成就
 */
async function showAchievements() {
    showScreen('achievement-screen');
    await updateAchievements();  // 刷新成就列表
}

/**
 * 显示个人中心
 */
async function showProfile() {
    showScreen('profile-screen');
    await updateProfileInfo();
}

/**
 * 更新个人中心信息
 */
async function updateProfileInfo() {
    const userId = appState.userId || getCurrentUserId();
    let user = null;
    
    if (userId) {
        try {
            user = await apiRequest(`/user/${userId}`);
            appState.userId = user.id;
            appState.stats = user.stats || appState.stats;
            
            if (user.avatar) {
                localStorage.setItem('userAvatar', user.avatar);
            } else {
                localStorage.removeItem('userAvatar');
            }
        } catch (error) {
            console.error('获取用户信息失败:', error);
        }
    }
    
    const studentName = user?.student_name || localStorage.getItem('studentName') || '学生';
    const username = user?.username || localStorage.getItem('username');
    const displayUsername = username || studentName || '未登录';
    const level = user?.level || 1;
    
    const profileNameEl = document.getElementById('profile-name');
    const profileUsernameEl = document.getElementById('profile-username');
    const profileStudentNameEl = document.getElementById('profile-student-name');
    const profileLevelEl = document.getElementById('profile-level') || 
                          document.getElementById('profile-student-level');
    
    if (profileNameEl) profileNameEl.textContent = studentName;
    if (profileUsernameEl) profileUsernameEl.textContent = displayUsername;
    if (profileStudentNameEl) profileStudentNameEl.textContent = studentName;
    if (profileLevelEl) profileLevelEl.textContent = level;
    
    const profileUsernameDisplayEl = document.getElementById('profile-username-display');
    if (profileUsernameDisplayEl) {
        profileUsernameDisplayEl.textContent = username ? '@' + username : '@' + displayUsername;
    }
    
    loadAvatar();
    bindAvatarUpload();
    
    const stats = appState.stats || {};
    const totalQuestions = stats.totalQuestions || 0;
    const correctCount = stats.correctCount || 0;
    const accuracy = totalQuestions > 0
        ? Math.round((correctCount / totalQuestions) * 100)
        : 0;
    
    const profileTotalEl = document.getElementById('profile-total');
    const profileCorrectEl = document.getElementById('profile-correct');
    const profileAccuracyEl = document.getElementById('profile-accuracy');
    const profilePerfectEl = document.getElementById('profile-perfect');
    const profileConsecutiveEl = document.getElementById('profile-consecutive-days');
    
    if (profileTotalEl) profileTotalEl.textContent = totalQuestions;
    if (profileCorrectEl) profileCorrectEl.textContent = correctCount;
    if (profileAccuracyEl) profileAccuracyEl.textContent = accuracy + '%';
    if (profilePerfectEl) profilePerfectEl.textContent = stats.perfectScore || 0;
    if (profileConsecutiveEl) profileConsecutiveEl.textContent = (stats.consecutiveDays || 0) + '天';
    
    if (document.getElementById('profile-total-time') && user) {
        const totalSeconds = user.total_study_time || 0;
        const hours = Math.floor(totalSeconds / 3600);
        const minutes = Math.floor((totalSeconds % 3600) / 60);
        const timeText = hours > 0 ? `${hours}小时${minutes}分钟` : `${minutes}分钟`;
        document.getElementById('profile-total-time').textContent = timeText;
    }
    
    if (document.getElementById('profile-register-date') && user?.created_at) {
        document.getElementById('profile-register-date').textContent =
            new Date(user.created_at).toLocaleDateString('zh-CN');
    }
    
    let unlockedCount = 0;
    let unlockedAchievements = [];
    if (appState.userId) {
        try {
            const response = await apiRequest(`/user/${appState.userId}/achievements`);
            unlockedCount = (response.unlocked_achievements || []).length;
            unlockedAchievements = response.unlocked_achievements || [];
        } catch (error) {
            console.error('获取成就列表失败:', error);
        }
    }
    const achievementsCountEl = document.getElementById('profile-achievements-count');
    if (achievementsCountEl) achievementsCountEl.textContent = unlockedCount;
    
    updateProfileBadges(unlockedAchievements);
    
    const xp = totalQuestions;
    const nextXp = level * 100;
    const progress = nextXp > 0 ? Math.min((xp % nextXp) / nextXp * 100, 100) : 0;
    
    const profileXpEl = document.getElementById('profile-xp');
    const profileNextXpEl = document.getElementById('profile-next-xp');
    const profileLevelProgressEl = document.getElementById('profile-level-progress');
    
    if (profileXpEl) profileXpEl.textContent = xp;
    if (profileNextXpEl) profileNextXpEl.textContent = nextXp;
    if (profileLevelProgressEl) profileLevelProgressEl.style.width = progress + '%';
    
    await renderStatsCharts();
}

/**
 * 更新个人中心成就徽章展示
 */
function updateProfileBadges(unlockedAchievements) {
    const container = document.getElementById('profile-badges-container');
    if (!container) return;
    
    // 定义要展示的徽章
    const badges = [
        { icon: '🌟', name: '初出茅庐', desc: '完成首次答题', condition: (stats) => stats.totalQuestions >= 1 },
        { icon: '🔥', name: '连续学习', desc: '连续学习7天', condition: (stats) => (stats.consecutiveDays || 0) >= 7 },
        { icon: '💯', name: '满分达人', desc: '获得10次满分', condition: (stats) => stats.perfectScore >= 10 },
        { icon: '📚', name: '学霸之路', desc: '答题超过1000题', condition: (stats) => stats.totalQuestions >= 1000 }
    ];
    
    // 清空容器
    container.innerHTML = '';
    
    // 生成徽章HTML
    badges.forEach(badge => {
        const isUnlocked = badge.condition(appState.stats);
        const badgeElement = document.createElement('div');
        badgeElement.className = `profile-badge-item${isUnlocked ? '' : ' locked'}`;
        badgeElement.innerHTML = `
            <div class="profile-badge-icon">${badge.icon}</div>
            <div class="profile-badge-name">${badge.name}</div>
            <div class="profile-badge-desc">${badge.desc}</div>
        `;
        container.appendChild(badgeElement);
    });
}

/**
 * 显示修改昵称弹窗
 */
function showEditNameModal() {
    const modal = document.getElementById('edit-name-modal');
    if (modal) {
        modal.style.display = 'flex';
        const input = document.getElementById('profile-edit-name');
        if (input) {
            input.value = localStorage.getItem('studentName') || '';
            setTimeout(() => input.focus(), 100);
        }
    }
}

/**
 * 关闭修改昵称弹窗
 */
function closeEditNameModal() {
    const modal = document.getElementById('edit-name-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

/**
 * 保存修改的昵称
 */
async function saveProfileName() {
    const newName = document.getElementById('profile-edit-name').value.trim();
    
    // 验证昵称长度
    if (!newName) {
        alert('请输入昵称！');
        return;
    }
    
    if (newName.length < 2 || newName.length > 10) {
        alert('昵称长度必须在2-10个字符之间！');
        return;
    }
    
    if (appState.userId) {
        try {
            await apiRequest(`/user/${appState.userId}/update`, 'POST', {
                student_name: newName
            });
            localStorage.setItem('studentName', newName);
            document.getElementById('student-name').textContent = newName;
            document.getElementById('profile-name').textContent = newName;
            document.getElementById('profile-student-name').textContent = newName;
            updateLoginStatus();
            alert('昵称修改成功！');
            closeEditNameModal();
        } catch (error) {
            console.error('更新昵称失败:', error);
            alert('更新失败，请重试');
        }
    } else {
        localStorage.setItem('studentName', newName);
        document.getElementById('student-name').textContent = newName;
        document.getElementById('profile-name').textContent = newName;
        document.getElementById('profile-student-name').textContent = newName;
        updateLoginStatus();
        alert('昵称修改成功！');
        closeEditNameModal();
    }
}

/**
 * 清除所有数据
 */
function clearAllData() {
    if (confirm('确定要清除所有学习数据吗？此操作不可恢复！')) {
        if (confirm('再次确认：清除后，所有答题记录、错题本、成就都将被删除！')) {
            try {
                // 清除本地存储
                localStorage.removeItem('quizUserId');
                localStorage.removeItem('studentName');
                localStorage.removeItem('quizUserToken');
                localStorage.removeItem('username');
                
                // 清除sessionStorage
                sessionStorage.clear();
                
                // 重置状态
                appState.userId = null;
                appState.stats = {
                    totalQuestions: 0,
                    correctCount: 0,
                    perfectScore: 0,
                    consecutiveDays: 0
                };
                appState.wrongBook = [];
                
                // 更新显示
                document.getElementById('student-name').textContent = '新学生';
                document.getElementById('student-level').textContent = '1';
                document.getElementById('total-questions').textContent = '0';
                document.getElementById('correct-count').textContent = '0';
                document.getElementById('accuracy-rate').textContent = '0%';
                
                updateLoginStatus();
                
                alert('数据已清除！');
                // 刷新页面
                window.location.reload();
            } catch (error) {
                console.error('清除数据失败:', error);
                alert('清除数据失败，请重试');
            }
        }
    }
}

/**
 * 更新成就显示
 */
async function updateAchievements() {
    const list = document.getElementById('achievements-list');
    if (!list) return;
    
    // 获取已解锁的成就
    let unlockedIds = [];
    if (appState.userId) {
        try {
            const response = await apiRequest(`/user/${appState.userId}/achievements`);
            unlockedIds = response.unlocked_achievements || [];
        } catch (error) {
            console.error('获取成就列表失败:', error);
        }
    }
    
    list.innerHTML = '';
    
    appState.achievements.forEach(ach => {
        const unlocked = unlockedIds.includes(ach.id);
        const div = document.createElement('div');
        div.className = 'achievement-item' + (unlocked ? '' : ' locked');
        div.innerHTML = `
            <div class="achievement-icon">${unlocked ? ach.icon : '🔒'}</div>
            <div class="achievement-info">
                <div class="achievement-name">${ach.name}</div>
                <div class="achievement-desc">${ach.desc}</div>
            </div>
            <div class="achievement-progress">
                <div class="achievement-status">${unlocked ? '✅' : '🔒'}</div>
            </div>
        `;
        list.appendChild(div);
    });
}

// ============== 账号安全功能 ==============

/**
 * 加载账号安全信息
 */
async function loadSecurityInfo() {
    const username = localStorage.getItem('username') || '未登录';
    const userId = localStorage.getItem('userId');
    
    const securityUsernameEl = document.getElementById('security-username');
    if (securityUsernameEl) {
        securityUsernameEl.textContent = username;
    }
    
    // 获取注册时间
    if (userId && document.getElementById('security-register-date')) {
        try {
            const user = await apiRequest(`/user/${userId}`);
            if (user.created_at) {
                const date = new Date(user.created_at);
                document.getElementById('security-register-date').textContent = date.toLocaleDateString('zh-CN');
            }
        } catch (error) {
            console.error('获取用户信息失败:', error);
        }
    }
}

/**
 * 修改密码
 */
async function changePassword() {
    const currentPassword = document.getElementById('current-password').value;
    const newPassword = document.getElementById('new-password').value;
    const confirmPassword = document.getElementById('confirm-password').value;
    
    if (!currentPassword || !newPassword || !confirmPassword) {
        alert('请填写所有密码字段！');
        return;
    }
    
    if (newPassword.length < 6) {
        alert('新密码长度至少6个字符！');
        return;
    }
    
    if (newPassword !== confirmPassword) {
        alert('两次输入的新密码不一致！');
        return;
    }
    
    try {
        const userId = localStorage.getItem('userId');
        const token = localStorage.getItem('authToken');
        
        const response = await fetch(`${API_BASE_URL}/user/${userId}/change-password`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                old_password: currentPassword,
                new_password: newPassword
            })
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            alert('密码修改成功！');
            // 清空表单
            document.getElementById('current-password').value = '';
            document.getElementById('new-password').value = '';
            document.getElementById('confirm-password').value = '';
        } else {
            alert(data.error || '密码修改失败');
        }
    } catch (error) {
        console.error('修改密码失败:', error);
        alert('网络错误，请稍后重试');
    }
}

/**
 * 绑定手机
 */
async function bindPhone() {
    const phone = document.getElementById('phone-number').value.trim();
    
    if (!phone) {
        alert('请输入手机号！');
        return;
    }
    
    // 简单的手机号验证
    const phoneRegex = /^1[3-9]\d{9}$/;
    if (!phoneRegex.test(phone)) {
        alert('请输入正确的手机号格式！');
        return;
    }
    
    try {
        const userId = localStorage.getItem('userId');
        const token = localStorage.getItem('authToken');
        
        const response = await fetch(`${API_BASE_URL}/user/${userId}/update`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ phone: phone })
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            alert('手机绑定成功！');
            document.getElementById('phone-number').value = '';
        } else {
            alert(data.error || '手机绑定失败');
        }
    } catch (error) {
        console.error('绑定手机失败:', error);
        alert('网络错误，请稍后重试');
    }
}

/**
 * 显示删除账号弹窗
 */
function showDeleteAccountModal() {
    const modal = document.getElementById('delete-account-modal');
    if (modal) {
        modal.style.display = 'flex';
        const input = document.getElementById('delete-confirm-input');
        if (input) {
            input.value = '';
            setTimeout(() => input.focus(), 100);
        }
    }
}

/**
 * 关闭删除账号弹窗
 */
function closeDeleteAccountModal() {
    const modal = document.getElementById('delete-account-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

/**
 * 确认删除账号
 */
async function confirmDeleteAccount() {
    const confirmText = document.getElementById('delete-confirm-input').value.trim();
    
    if (confirmText !== 'DELETE') {
        alert('请输入"DELETE"确认删除！');
        return;
    }
    
    try {
        const userId = localStorage.getItem('userId');
        const token = localStorage.getItem('authToken');
        
        const response = await fetch(`${API_BASE_URL}/user/${userId}/delete`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            }
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            alert('账号已注销，感谢使用！');
            // 清除本地存储
            localStorage.clear();
            // 跳转到登录页
            window.location.href = 'login.html';
        } else {
            alert(data.error || '注销失败');
        }
    } catch (error) {
        console.error('注销账号失败:', error);
        alert('网络错误，请稍后重试');
    }
}

// ============== 头像上传功能 ==============

/**
 * 设置头像到容器元素
 */
function setAvatarOnElement(container, src) {
    if (!container) return;
    const resolvedSrc = src || DEFAULT_AVATAR;
    let img = container.querySelector('img');
    if (!img) {
        container.innerHTML = `<img src="${resolvedSrc}" alt="头像">`;
        img = container.querySelector('img');
    } else if (img.getAttribute('src') !== resolvedSrc) {
        img.src = resolvedSrc;
    }
    if (img) {
        img.onerror = function() {
            this.onerror = null;
            this.src = DEFAULT_AVATAR;
        };
    }
}

/**
 * 加载头像
 */
function loadAvatar() {
    const avatarData = localStorage.getItem('userAvatar');
    const src = avatarData || DEFAULT_AVATAR;
    setAvatarOnElement(document.getElementById('profile-avatar-display'), src);
    setAvatarOnElement(document.getElementById('user-avatar'), src);
}

/**
 * 绑定头像上传事件
 */
function bindAvatarUpload() {
    const avatarUpload = document.getElementById('avatar-upload');
    if (avatarUpload) {
        // 移除可能已有的监听器
        avatarUpload.removeEventListener('change', handleAvatarUpload);
        // 添加新的监听器
        avatarUpload.addEventListener('change', handleAvatarUpload);
    }
}

/**
 * 处理头像上传
 */
function handleAvatarUpload(event) {
    const file = event.target.files[0];
    
    if (!file) {
        return;
    }
    
    // 验证文件类型
    if (!file.type.startsWith('image/')) {
        alert('请选择图片文件！');
        return;
    }
    
    // 验证文件大小（限制2MB）
    if (file.size > 2 * 1024 * 1024) {
        alert('图片大小不能超过2MB！');
        return;
    }
    
    // 读取文件并转换为base64
    const reader = new FileReader();
    reader.onload = async function(e) {
        const imageData = e.target.result;
        
        // 保存到localStorage
        localStorage.setItem('userAvatar', imageData);
        
        // 更新个人中心的头像显示
        const profileAvatarDisplay = document.getElementById('profile-avatar-display');
        if (profileAvatarDisplay) {
            profileAvatarDisplay.innerHTML = `<img src="${imageData}" alt="头像">`;
        }
        
        // 更新首页的头像显示
        const homeAvatar = document.getElementById('user-avatar');
        if (homeAvatar) {
            homeAvatar.innerHTML = `<img src="${imageData}" alt="头像">`;
        }
        
        // 如果已登录，同时上传到后端
        const saveResult = await saveAvatarToBackend(imageData);
        
        if (saveResult) {
            alert('头像更新成功！已保存到服务器');
        } else {
            alert('头像已保存到本地，但未能同步到服务器（可能未登录）');
        }
    };
    reader.readAsDataURL(file);
}

/**
 * 保存头像到后端
 * @returns {boolean} 是否保存成功
 */
async function saveAvatarToBackend(imageData) {
    try {
        const userId = localStorage.getItem('userId');
        console.log('📤 准备保存头像到后端, userId:', userId);
        
        if (!userId) {
            console.warn('⚠️ 用户未登录，无法保存头像到服务器');
            return false;
        }
        
        console.log('📡 发送请求到:', `${API_BASE_URL}/user/${userId}/avatar`);
        console.log('📸 头像数据长度:', imageData.length);
        
        const response = await fetch(`${API_BASE_URL}/user/${userId}/avatar`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ avatar: imageData })
        });
        
        console.log('📥 收到响应, 状态码:', response.status);
        
        const data = await response.json();
        console.log('📦 响应数据:', data);
        
        if (response.ok && data.success) {
            console.log('✓ 头像已同步到服务器');
            return true;
        } else {
            console.error('❌ 保存失败:', data.error || '未知错误');
            return false;
        }
    } catch (error) {
        console.error('❌ 保存头像到服务器失败:', error);
        // 即使服务器保存失败，本地已经保存，不影响使用
        return false;
    }
}

// ============== 排行榜功能 ==============

/**
 * 加载排行榜数据
 */
async function loadLeaderboard() {
    const leaderboardList = document.getElementById('leaderboard-list');
    if (!leaderboardList) return;
    
    try {
        console.log('📊 开始加载排行榜数据...');
        const data = await apiRequest('/leaderboard');
        console.log('📦 排行榜原始数据:', data);
        
        const leaderboard = data.leaderboard || [];
        console.log('📋 排行榜用户数量:', leaderboard.length);
        
        // 打印前3个用户的头像信息
        leaderboard.slice(0, 3).forEach((user, idx) => {
            console.log(`用户${idx + 1}:`, {
                name: user.student_name || user.username,
                hasAvatar: !!user.avatar,
                avatarLength: user.avatar ? user.avatar.length : 0
            });
        });
        
        // 更新统计概览
        const totalUsers = data.total_users || 0;
        let totalAnswers = 0;
        let totalCorrect = 0;
        
        leaderboard.forEach(user => {
            totalAnswers += user.total_questions;
            totalCorrect += user.correct_count;
        });
        
        const totalUsersEl = document.getElementById('total-users');
        const totalAnswersEl = document.getElementById('total-answers');
        const totalCorrectEl = document.getElementById('total-correct');
        
        if (totalUsersEl) totalUsersEl.textContent = totalUsers;
        if (totalAnswersEl) totalAnswersEl.textContent = totalAnswers;
        if (totalCorrectEl) totalCorrectEl.textContent = totalCorrect;
        
        // 渲染排行榜
        if (leaderboard.length === 0) {
            leaderboardList.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">📊</div>
                    <p>暂无排行榜数据</p>
                    <p class="empty-desc">开始答题，登上排行榜！</p>
                </div>
            `;
            return;
        }
        
        let html = '';
        leaderboard.forEach((user, index) => {
            const rank = user.rank;
            let rankIcon = '';
            if (rank === 1) rankIcon = '🥇';
            else if (rank === 2) rankIcon = '🥈';
            else if (rank === 3) rankIcon = '🥉';
            else rankIcon = rank;
            
            const isCurrentUser = user.id == (getCurrentUserId() || localStorage.getItem('userId'));
            const currentClass = isCurrentUser ? 'current-user' : '';
            
            // 使用后端返回的头像数据，如果没有则显示默认头像
            const avatarHTML = user.avatar ? `<img src="${user.avatar}" alt="头像">` : `<img src="${DEFAULT_AVATAR}" alt="默认头像">`;
            
            html += `
                <div class="leaderboard-item ${currentClass}">
                    <div class="leaderboard-rank">${rankIcon}</div>
                    <div class="leaderboard-avatar">
                        ${avatarHTML}
                    </div>
                    <div class="leaderboard-info">
                        <div class="leaderboard-name">
                            ${user.student_name || user.username}
                            ${isCurrentUser ? '<span class="current-badge">我</span>' : ''}
                        </div>
                        <div class="leaderboard-meta">
                            <span class="level-badge-small">⭐ Lv.${user.level}</span>
                            <span class="accuracy-badge">正确率 ${user.accuracy}%</span>
                        </div>
                    </div>
                    <div class="leaderboard-stats">
                        <div class="stat-item">
                            <div class="stat-value-large">${user.correct_count}</div>
                            <div class="stat-label-small">答对</div>
                        </div>
                        <div class="stat-divider"></div>
                        <div class="stat-item">
                            <div class="stat-value-large">${user.total_questions}</div>
                            <div class="stat-label-small">总计</div>
                        </div>
                    </div>
                </div>
            `;
        });
        
        leaderboardList.innerHTML = html;
        
    } catch (error) {
        console.error('加载排行榜失败:', error);
        leaderboardList.innerHTML = `
            <div class="error-state">
                <div class="error-icon">⚠️</div>
                <p>加载失败，请重试</p>
                <button class="retry-btn" onclick="loadLeaderboard()">重试</button>
            </div>
        `;
    }
}

/**
 * 获取头像HTML
 */
function getAvatarHTML(userId) {
    // 尝试从 localStorage 获取头像
    const userAvatar = localStorage.getItem('userAvatar');
    const currentUserId = getCurrentUserId() || localStorage.getItem('userId');
    
    if (userId == currentUserId && userAvatar) {
        return `<img src="${userAvatar}" alt="头像">`;
    }
    
    return `<img src="${DEFAULT_AVATAR}" alt="默认头像">`;
}

/**
 * 渲染学习数据统计图表
 */
async function renderStatsCharts() {
    const userId = appState.userId || getCurrentUserId();
    if (!userId) {
        showChartEmpty('daily-chart', 'daily-chart-empty', true, '请先登录后查看学习数据');
        showChartEmpty('subject-chart', 'subject-chart-empty', true, '请先登录后查看学习数据');
        return;
    }
    
    if (typeof Chart === 'undefined') {
        console.warn('Chart.js 未加载，跳过图表渲染');
        showChartEmpty('daily-chart', 'daily-chart-empty', true, '图表库加载失败，请刷新页面重试');
        showChartEmpty('subject-chart', 'subject-chart-empty', true, '图表库加载失败，请刷新页面重试');
        return;
    }
    
    try {
        const data = await apiRequest(`/user/${userId}/stats/detail`);
        
        if (data.summary) {
            updateChartsSummary(data.summary);
            if (document.getElementById('profile-accuracy') && data.summary.accuracy !== undefined) {
                document.getElementById('profile-accuracy').textContent = data.summary.accuracy + '%';
            }
        }
        
        renderDailyChart(data.daily_stats || []);
        renderSubjectChart(data.subject_stats || []);
    } catch (error) {
        console.error('加载统计数据失败:', error);
        showChartEmpty('daily-chart', 'daily-chart-empty', true, '加载失败，请刷新重试');
        showChartEmpty('subject-chart', 'subject-chart-empty', true, '加载失败，请刷新重试');
    }
}

/**
 * 更新图表汇总信息
 */
function updateChartsSummary(summary) {
    const container = document.getElementById('profile-charts-summary');
    if (!container) return;
    
    container.innerHTML = `
        <div class="charts-summary-item">
            <div class="charts-summary-value">${summary.weekly_total || 0}</div>
            <div class="charts-summary-label">近7天答题</div>
        </div>
        <div class="charts-summary-item">
            <div class="charts-summary-value">${summary.accuracy || 0}%</div>
            <div class="charts-summary-label">总正确率</div>
        </div>
        <div class="charts-summary-item">
            <div class="charts-summary-value">${summary.correct_count || 0}</div>
            <div class="charts-summary-label">累计答对</div>
        </div>
        <div class="charts-summary-item">
            <div class="charts-summary-value">${summary.total_questions || 0}</div>
            <div class="charts-summary-label">累计答题</div>
        </div>
    `;
}

/**
 * 显示/隐藏图表空状态
 */
function showChartEmpty(canvasId, emptyId, show, message) {
    const canvas = document.getElementById(canvasId);
    const empty = document.getElementById(emptyId);
    if (empty) {
        empty.style.display = show ? 'flex' : 'none';
        if (message) empty.textContent = message;
    }
    if (canvas) canvas.style.display = show ? 'none' : 'block';
}

/**
 * 渲染每日答题趋势图
 */
function renderDailyChart(dailyStats) {
    const canvas = document.getElementById('daily-chart');
    if (!canvas) return;
    
    const total = dailyStats.reduce((sum, s) => sum + (s.count || 0), 0);
    if (total === 0) {
        if (window.dailyChartInstance) {
            window.dailyChartInstance.destroy();
            window.dailyChartInstance = null;
        }
        showChartEmpty('daily-chart', 'daily-chart-empty', true, '暂无答题记录，快去刷题吧！');
        return;
    }
    
    showChartEmpty('daily-chart', 'daily-chart-empty', false);
    
    if (window.dailyChartInstance) {
        window.dailyChartInstance.destroy();
    }
    
    const ctx = canvas.getContext('2d');
    const labels = dailyStats.map(s => {
        const parts = (s.date || '').split('-');
        return parts.length >= 3 ? `${parts[1]}-${parts[2]}` : s.date;
    });
    const counts = dailyStats.map(s => s.count || 0);
    
    window.dailyChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: '答题数',
                data: counts,
                backgroundColor: 'rgba(99, 102, 241, 0.75)',
                borderColor: '#6366f1',
                borderWidth: 1,
                borderRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: '最近7天答题趋势',
                    font: { size: 16, weight: 'bold' }
                },
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (ctx) => `答题 ${ctx.parsed.y} 道`
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { stepSize: 1, precision: 0 }
                }
            }
        }
    });
}

/**
 * 渲染科目正确率饼图
 */
function renderSubjectChart(subjectStats) {
    const canvas = document.getElementById('subject-chart');
    if (!canvas) return;
    
    const subjectNames = {
        'math': '数学',
        'chinese': '语文',
        'english': '英语',
        'science': '科学',
        'history': '历史'
    };
    
    const withData = subjectStats.filter(s => (s.total || 0) > 0);
    if (withData.length === 0) {
        if (window.subjectChartInstance) {
            window.subjectChartInstance.destroy();
            window.subjectChartInstance = null;
        }
        showChartEmpty('subject-chart', 'subject-chart-empty', true, '暂无科目数据，选择科目开始答题');
        return;
    }
    
    showChartEmpty('subject-chart', 'subject-chart-empty', false);
    
    if (window.subjectChartInstance) {
        window.subjectChartInstance.destroy();
    }
    
    const ctx = canvas.getContext('2d');
    const labels = withData.map(s => subjectNames[s.subject] || s.subject);
    const accuracies = withData.map(s => s.accuracy || 0);
    const totals = withData.map(s => s.total || 0);
    const colors = ['#6366f1', '#f59e0b', '#10b981', '#ec4899', '#8b5cf6'];
    
    window.subjectChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: '正确率 (%)',
                data: accuracies,
                backgroundColor: colors.slice(0, labels.length).map(c => c + 'cc'),
                borderColor: colors.slice(0, labels.length),
                borderWidth: 2,
                borderRadius: 6
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: '各科正确率',
                    font: { size: 16, weight: 'bold' }
                },
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (ctx) => {
                            const idx = ctx.dataIndex;
                            const total = totals[idx];
                            const correct = withData[idx].correct || 0;
                            return [
                                `正确率: ${ctx.parsed.x}%`,
                                `答对 ${correct} / 共 ${total} 题`
                            ];
                        }
                    }
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                        callback: (v) => v + '%'
                    }
                }
            }
        }
    });
}

/**
 * 加载每日任务
 */
async function loadDailyTask() {
    const userId = getCurrentUserId();
    if (!userId) return;
    
    try {
        const data = await apiRequest(`/user/${userId}/daily-task`);
        const task = data.task;
        
        const taskCard = document.getElementById('daily-task-card');
        const statusText = document.getElementById('task-status-text');
        const progressBar = document.getElementById('task-progress-bar');
        const infoText = document.getElementById('task-info-text');
        
        if (taskCard && statusText && progressBar && infoText) {
            const percentage = (task.completed_questions / task.target_questions * 100);
            
            progressBar.style.width = percentage + '%';
            infoText.textContent = `已完成 ${task.completed_questions} / ${task.target_questions} 题`;
            
            if (task.is_completed) {
                statusText.textContent = '✅ 已完成';
                statusText.classList.add('completed');
            } else {
                statusText.textContent = '进行中';
                statusText.classList.remove('completed');
            }
        }
    } catch (error) {
        console.error('加载每日任务失败:', error);
    }
}

/**
 * 更新每日任务进度
 */
async function updateDailyTaskProgress() {
    const userId = getCurrentUserId();
    if (!userId) return;
    
    try {
        // 获取今日已答题数
        const today = new Date().toISOString().split('T')[0];
        const response = await fetch(`${API_BASE_URL}/answer/today-count?user_id=${userId}&date=${today}`);
        const data = await response.json();
        const todayCount = data.count || 0;
        
        // 更新任务进度
        await apiRequest(`/user/${userId}/daily-task/update`, 'POST', {
            completed_questions: todayCount
        });
        
        // 刷新任务显示
        await loadDailyTask();
    } catch (error) {
        console.error('更新任务进度失败:', error);
    }
}

// ============== 启动应用 ==============
// 页面若已声明 __customPageInit，则由页面自行调用 initApp
if (!window.__customPageInit) {
    window.addEventListener('load', () => initApp());
}

// 导出 logout 函数供全局调用

/**
 * AI解析错题
 */
async function explainWithAI(wrongItemId, btn) {
    const userId = getCurrentUserId();
    if (!userId) {
        alert('请先登录');
        return;
    }
    
    // 获取错题信息
    const wrongItem = appState.wrongBook.find(w => w.id === wrongItemId);
    if (!wrongItem) return;
    
    btn.disabled = true;
    btn.textContent = '🤔 AI思考中...';
    
    try {
        const response = await apiRequest('/ai/explain-question', 'POST', {
            user_id: userId,
            question: wrongItem.question,
            user_answer: wrongItem.user_answer || '未作答',
            correct_answer: wrongItem.answer,
            subject: wrongItem.subject
        });
        
        // 显示解析结果
        showAIExplanation(wrongItemId, response.explanation);
        
        btn.textContent = '✅ 已解析';
        
        // 显示剩余次数
        if (response.remaining_quota !== undefined) {
            console.log(`本月剩余AI解析次数：${response.remaining_quota}`);
        }
        
    } catch (error) {
        if (error.response && error.response.need_upgrade) {
            showUpgradeModal();
        } else {
            alert('AI解析失败，请稍后重试');
        }
        btn.disabled = false;
        btn.textContent = '🤖 AI解析';
    }
}

/**
 * 显示AI解析内容
 */
function showAIExplanation(wrongItemId, explanation) {
    const explanationDiv = document.getElementById(`ai-explanation-${wrongItemId}`);
    if (!explanationDiv) return;
    
    // 将Markdown格式转换为HTML（简单实现）
    const htmlContent = explanation
        .replace(/\n\n/g, '</p><p>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/(\d+)\./g, '<br>$1.')
        .replace(/\n/g, '<br>');
    
    explanationDiv.innerHTML = `<div class="ai-explanation-inner"><p>${htmlContent}</p></div>`;
    explanationDiv.classList.add('show');
}

/**
 * 显示升级会员弹窗
 */
function showUpgradeModal() {
    // 检查是否已经存在弹窗
    const existingModal = document.getElementById('upgrade-modal');
    if (existingModal) {
        existingModal.style.display = 'flex';
        return;
    }
    
    const modalHTML = `
        <div class="modal upgrade-modal" id="upgrade-modal" style="display: flex;">
            <div class="modal-content upgrade-modal-content">
                <div class="modal-header">
                    <h2>🌟 升级VIP会员</h2>
                    <button class="modal-close" onclick="closeUpgradeModal()">×</button>
                </div>
                <div class="modal-body">
                    <div class="upgrade-benefit">
                        <h3>✨ VIP专属权益</h3>
                        <ul>
                            <li>✅ 无限次AI智能解析</li>
                            <li>✅ 个性化学习计划</li>
                            <li>✅ AI学习报告</li>
                            <li>✅ 优先客服支持</li>
                        </ul>
                    </div>
                    <div class="upgrade-plans">
                        <div class="plan-card">
                            <h4>月度VIP</h4>
                            <div class="plan-price">¥1/月</div>
                            <button class="subscribe-btn" onclick="subscribe('monthly')">立即开通</button>
                        </div>
                        <div class="plan-card recommended">
                            <h4>年度VIP</h4>
                            <div class="plan-price">¥10/年</div>
                            <div class="plan-badge">省¥2</div>
                            <button class="subscribe-btn" onclick="subscribe('yearly')">立即开通</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    document.body.insertAdjacentHTML('beforeend', modalHTML);
}

function closeUpgradeModal() {
    const modal = document.getElementById('upgrade-modal');
    if (modal) modal.remove();
}

/**
 * 订阅VIP
 */
async function subscribe(type) {
    const userId = getCurrentUserId();
    if (!userId) {
        alert('请先登录');
        return;
    }
    
    if (!confirm(`确定要开通${type === 'monthly' ? '月度' : '年度'}VIP吗？`)) {
        return;
    }
    
    try {
        const response = await apiRequest('/subscription/create', 'POST', {
            user_id: userId,
            type: type
        });
        
        if (response.success) {
            alert(`🎉 开通成功！\n到期时间：${response.end_date}`);
            closeUpgradeModal();
        }
    } catch (error) {
        alert('开通失败，请稍后重试');
    }
}
if (typeof logout === 'function') {
    window.logout = logout;
}
