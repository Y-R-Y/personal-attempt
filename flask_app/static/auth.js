/**
 * 认证模块 - 登录/注册
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
 * 快速开始（已禁用，需要登录）
 */
function quickStart() {
    // 显示登录提示
    alert('请先登录后再使用，登录可以保存学习进度哦！');
}

/**
 * 显示注册页面
 */
function showRegister() {
    document.getElementById('login-form').classList.remove('active');
    document.getElementById('register-form').classList.add('active');
}

/**
 * 显示登录页面
 */
function showLogin() {
    document.getElementById('register-form').classList.remove('active');
    document.getElementById('login-form').classList.add('active');
}

/**
 * 显示错误信息
 */
function showError(element, message) {
    element.textContent = message;
    element.style.display = 'block';
    
    // 3 秒后自动隐藏
    setTimeout(() => {
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
    
    // 跳转到登录页
    window.location.href = 'login.html';
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

// 导出 logout 函数到全局作用域
window.logout = logout;
