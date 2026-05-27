/**
 * 认证模块 - 登录/注册/找回密码
 * 依赖：config.js（先加载）
 */

/**
 * 处理登录
 */
async function handleLogin(event) {
    event.preventDefault();
    
    const username = document.getElementById('login-username').value.trim();
    const password = document.getElementById('login-password').value;
    const errorDiv = document.getElementById('login-error');
    
    try {
        const response = await fetch(`${API_BASE_URL}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password })
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            // 清除旧用户的头像缓存
            localStorage.removeItem('userAvatar');
            
            // 保存 Token 和用户信息
            localStorage.setItem('authToken', data.token);
            localStorage.setItem('userId', data.user_id);
            localStorage.setItem('quizUserId', data.user_id);
            localStorage.setItem('username', data.username);
            localStorage.setItem('studentName', data.student_name || data.username);
            
            console.log('✓ 登录成功:', data.username, '昵称:', data.student_name);
            
            // 跳转到之前访问的页面，或者首页
            const returnUrl = localStorage.getItem('loginReturnUrl');
            if (returnUrl) {
                localStorage.removeItem('loginReturnUrl');
                window.location.href = returnUrl;
            } else {
                window.location.href = 'index.html';
            }
        } else {
            showError(errorDiv, data.error || '登录失败');
        }
    } catch (error) {
        showError(errorDiv, '网络错误，请检查后端服务是否启动');
    }
}

/**
 * 处理注册
 */
async function handleRegister(event) {
    event.preventDefault();
    
    const username = document.getElementById('register-username').value.trim();
    const password = document.getElementById('register-password').value;
    const confirm = document.getElementById('register-confirm').value;
    const studentName = document.getElementById('register-student-name').value.trim();
    const phone = document.getElementById('register-phone').value.trim();
    const errorDiv = document.getElementById('register-error');
    
    // 验证密码
    if (password !== confirm) {
        showError(errorDiv, '两次输入的密码不一致');
        return;
    }
    
    // 验证手机号
    if (!phone || phone.length !== 11 || !/^\d{11}$/.test(phone)) {
        showError(errorDiv, '请输入有效的 11 位手机号码');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/auth/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, password, student_name: studentName, phone })
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            // 清除旧用户的头像缓存
            localStorage.removeItem('userAvatar');
            
            // 保存 Token 和用户信息
            localStorage.setItem('authToken', data.token);
            localStorage.setItem('userId', data.user_id);
            localStorage.setItem('quizUserId', data.user_id);
            localStorage.setItem('username', data.username);
            localStorage.setItem('studentName', studentName || data.username);
            
            console.log('✓ 注册成功:', data.username, '昵称:', studentName || data.username);
            
            // 跳转到之前访问的页面，或者首页
            const returnUrl = localStorage.getItem('loginReturnUrl');
            if (returnUrl) {
                localStorage.removeItem('loginReturnUrl');
                window.location.href = returnUrl;
            } else {
                window.location.href = 'index.html';
            }
        } else {
            showError(errorDiv, data.error || '注册失败');
        }
    } catch (error) {
        showError(errorDiv, '网络错误，请检查后端服务是否启动');
    }
}

/**
 * 显示找回密码页面
 */
function showForgotPassword(event) {
    if (event) event.preventDefault();
    hideAllForms();
    document.getElementById('forgot-password-form').classList.add('active');
    // 重置到步骤 1
    showForgotStep(1);
    // 清空输入
    document.getElementById('forgot-username').value = '';
    document.getElementById('forgot-phone').value = '';
    document.getElementById('forgot-new-password').value = '';
    document.getElementById('forgot-confirm-password').value = '';
    // 隐藏错误和成功
    document.getElementById('forgot-error-1').style.display = 'none';
    document.getElementById('forgot-error-2').style.display = 'none';
    document.getElementById('forgot-error-3').style.display = 'none';
    document.getElementById('forgot-success').style.display = 'none';
}

/**
 * 找回密码步骤一：验证用户名
 */
var forgotUsername = '';  // 保存已验证的用户名

async function handleForgotStep1(event) {
    event.preventDefault();
    
    var username = document.getElementById('forgot-username').value.trim();
    var errorDiv = document.getElementById('forgot-error-1');
    
    if (!username) {
        showError(errorDiv, '请输入用户名');
        return;
    }
    
    try {
        var response = await fetch(API_BASE_URL + '/auth/check-username', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: username })
        });
        
        var data = await response.json();
        
        if (response.ok && data.exists) {
            forgotUsername = username;
            showForgotStep(2);
        } else {
            showError(errorDiv, data.error || '该用户名不存在');
        }
    } catch (error) {
        showError(errorDiv, '网络错误，请检查后端服务是否启动');
    }
}

/**
 * 找回密码步骤二：验证手机号
 */
async function handleForgotStep2(event) {
    event.preventDefault();
    
    var phone = document.getElementById('forgot-phone').value.trim();
    var errorDiv = document.getElementById('forgot-error-2');
    
    if (!phone || phone.length !== 11 || !/^\d{11}$/.test(phone)) {
        showError(errorDiv, '请输入有效的 11 位手机号码');
        return;
    }
    
    try {
        var response = await fetch(API_BASE_URL + '/auth/verify-phone', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: forgotUsername, phone: phone })
        });
        
        var data = await response.json();
        
        if (response.ok && data.match) {
            showForgotStep(3);
        } else {
            showError(errorDiv, data.error || '手机号验证失败');
        }
    } catch (error) {
        showError(errorDiv, '网络错误，请检查后端服务是否启动');
    }
}

/**
 * 找回密码步骤三：设置新密码
 */
async function handleForgotStep3(event) {
    event.preventDefault();
    
    var newPassword = document.getElementById('forgot-new-password').value;
    var confirmPassword = document.getElementById('forgot-confirm-password').value;
    var errorDiv = document.getElementById('forgot-error-3');
    
    if (newPassword !== confirmPassword) {
        showError(errorDiv, '两次输入的密码不一致');
        return;
    }
    
    if (newPassword.length < 6) {
        showError(errorDiv, '新密码长度不能少于6位');
        return;
    }
    
    try {
        var response = await fetch(API_BASE_URL + '/auth/reset-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: forgotUsername, new_password: newPassword })
        });
        
        var data = await response.json();
        
        if (response.ok && data.success) {
            // 显示成功提示
            document.getElementById('forgot-step-1').style.display = 'none';
            document.getElementById('forgot-step-2').style.display = 'none';
            document.getElementById('forgot-step-3').style.display = 'none';
            document.getElementById('forgot-success').style.display = 'block';
            // 更新步骤指示器全部完成
            document.getElementById('step-indicator-1').classList.add('done');
            document.getElementById('step-indicator-2').classList.add('done');
            document.getElementById('step-indicator-3').classList.add('done');
        } else {
            showError(errorDiv, data.error || '重置失败');
        }
    } catch (error) {
        showError(errorDiv, '网络错误，请检查后端服务是否启动');
    }
}

/**
 * 显示找回密码的指定步骤
 */
function showForgotStep(step) {
    var step1 = document.getElementById('forgot-step-1');
    var step2 = document.getElementById('forgot-step-2');
    var step3 = document.getElementById('forgot-step-3');
    var success = document.getElementById('forgot-success');
    var indicator1 = document.getElementById('step-indicator-1');
    var indicator2 = document.getElementById('step-indicator-2');
    var indicator3 = document.getElementById('step-indicator-3');
    
    step1.style.display = 'none';
    step2.style.display = 'none';
    step3.style.display = 'none';
    success.style.display = 'none';
    indicator1.classList.remove('active', 'done');
    indicator2.classList.remove('active', 'done');
    indicator3.classList.remove('active', 'done');
    
    if (step === 1) {
        step1.style.display = 'block';
        indicator1.classList.add('active');
    } else if (step === 2) {
        step2.style.display = 'block';
        indicator1.classList.add('done');
        indicator2.classList.add('active');
    } else if (step === 3) {
        step3.style.display = 'block';
        indicator1.classList.add('done');
        indicator2.classList.add('done');
        indicator3.classList.add('active');
    }
}

/**
 * 快速开始（游客模式）
 * 设置 quickStart 标记，跳过登录检查，直接进入首页
 */
function quickStart() {
    // 设置游客模式标记，避免 initAuth() 拦截
    localStorage.setItem('quickStart', '1');
    // 清除可能残留的登录凭证
    localStorage.removeItem('authToken');
    localStorage.removeItem('userId');
    localStorage.removeItem('quizUserId');
    localStorage.removeItem('username');
    localStorage.removeItem('studentName');
    // 跳转到首页（游客模式）
    window.location.href = 'index.html';
}

/**
 * 隐藏所有表单
 */
function hideAllForms() {
    document.getElementById('login-form').classList.remove('active');
    document.getElementById('register-form').classList.remove('active');
    document.getElementById('forgot-password-form').classList.remove('active');
}

/**
 * 显示注册页面
 */
function showRegister() {
    hideAllForms();
    document.getElementById('register-form').classList.add('active');
}

/**
 * 显示登录页面
 */
function showLogin() {
    hideAllForms();
    document.getElementById('login-form').classList.add('active');
}

/**
 * 显示错误信息
 */
function showError(element, message) {
    element.textContent = message;
    element.style.display = 'block';
    
    // 3 秒后自动隐藏
    setTimeout(function() {
        element.style.display = 'none';
    }, 5000);
}

/**
 * 检查登录状态
 */
function checkAuth() {
    const token = localStorage.getItem('authToken');
    const userId = localStorage.getItem('userId');
    
    if (token && userId) {
        return {
            isLoggedIn: true,
            token: token,
            userId: userId,
            username: localStorage.getItem('username'),
            studentName: localStorage.getItem('studentName')
        };
    }
    
    return { isLoggedIn: false };
}

/**
 * 登出
 */
async function logout() {
    const token = localStorage.getItem('authToken');
    
    try {
        await fetch(`${API_BASE_URL}/auth/logout`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
    } catch (error) {
        console.error('登出失败:', error);
    }
    
    // 清除本地存储
    localStorage.removeItem('authToken');
    localStorage.removeItem('userId');
    localStorage.removeItem('quizUserId');
    localStorage.removeItem('username');
    localStorage.removeItem('studentName');
    localStorage.removeItem('quickStart');
    localStorage.removeItem('userAvatar');  // 清除头像缓存
    
    // 跳转到首页（游客模式）
    window.location.href = 'index.html';
}

// 页面加载时检查是否需要跳转到登录页
function initAuth() {
    const currentPath = window.location.pathname;
    const isLoginPage = currentPath.includes('login.html');
    
    // 如果在其他页面且未登录，跳转到登录页
    if (!isLoginPage && !localStorage.getItem('authToken') && !localStorage.getItem('quickStart')) {
        // 可选：强制登录
        // window.location.href = 'login.html';
    }
}

// 初始化
initAuth();

// 如果 URL 参数指定了 tab=register，自动切换到注册表单
(function() {
    var params = new URLSearchParams(window.location.search);
    if (params.get('tab') === 'register') {
        // DOM 可能还没加载完，等一等
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', function() { showRegister(); });
        } else {
            showRegister();
        }
    }
})();

// 导出 logout 函数到全局作用域
window.logout = logout;
