// 全局变量
let selectedAuditFile = null;
let filesToUpload = []; // 新增：存储拖拽或选中的文件

// --- 导航切换 ---
function switchTab(panelId) {
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));

    document.getElementById(panelId).classList.add('active');

    const icons = {
        'audit-panel': 'fa-shield-halved',
        'ip-panel': 'fa-book-open',
        'admin-panel': 'fa-user-gear'
    };
    const iconClass = icons[panelId];
    document.querySelectorAll('.nav-item').forEach(btn => {
        if(btn.innerHTML.includes(iconClass)) btn.classList.add('active');
    });

    if(panelId === 'admin-panel' && !document.getElementById('admin-view').classList.contains('hidden')) {
        loadRules();
    }
}

// --- 业务审查功能 ---
document.getElementById('audit-file').addEventListener('change', function(e) {
    if(e.target.files[0]) {
        selectedAuditFile = e.target.files[0];
        document.getElementById('file-name-display').innerText = selectedAuditFile.name;
        document.getElementById('clear-file-btn').classList.remove('hidden');
    }
});

function clearSelectedFile() {
    selectedAuditFile = null;
    document.getElementById('audit-file').value = '';
    document.getElementById('file-name-display').innerText = '未选择文件';
    document.getElementById('clear-file-btn').classList.add('hidden');
}

async function startAudit() {
    const text = document.getElementById('audit-text').value;
    const resultBox = document.getElementById('audit-result');

    if(!text && !selectedAuditFile) {
        alert("请先输入文本或上传文件！");
        return;
    }

    resultBox.innerHTML = '<div style="text-align:center; padding-top:50px;"><i class="fa-solid fa-spinner fa-spin fa-2x"></i><br><br>正在进行法律底座 RAG 全维扫描...</div>';

    const formData = new FormData();
    formData.append('text', text);
    if(selectedAuditFile) {
        formData.append('file', selectedAuditFile);
    }

    try {
        const response = await fetch('/api/audit', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        if(data.result) {
            resultBox.innerHTML = data.result;
        } else {
            resultBox.innerText = "Error: " + (data.error || "未知错误");
        }
    } catch (err) {
        resultBox.innerText = "网络请求失败";
    }
}

// --- 知识产权助手 ---
async function sendIpQuery() {
    const input = document.getElementById('ip-query');
    const query = input.value;
    if(!query) return;

    const chatBox = document.getElementById('chat-history');

    chatBox.innerHTML += `<div class="message msg-user">${query}</div>`;
    input.value = '';

    chatBox.innerHTML += `<div class="message msg-ai" id="temp-loading">思考中...</div>`;
    chatBox.scrollTop = chatBox.scrollHeight;

    try {
        const response = await fetch('/api/chat_ip', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({query: query})
        });
        const data = await response.json();

        document.getElementById('temp-loading').remove();
        if(data.result) {
            chatBox.innerHTML += `<div class="message msg-ai">${data.result}</div>`;
        } else {
            chatBox.innerHTML += `<div class="message msg-ai">发生错误</div>`;
        }
    } catch(err) {
        document.getElementById('temp-loading').remove();
        chatBox.innerHTML += `<div class="message msg-ai">网络异常</div>`;
    }
    chatBox.scrollTop = chatBox.scrollHeight;
}

// --- 管理端功能 ---
async function adminLogin() {
    const pwd = document.getElementById('admin-pwd').value;
    const res = await fetch('/api/verify_admin', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({password: pwd})
    });
    const data = await res.json();

    if(data.status === 'success') {
        document.getElementById('login-view').classList.add('hidden');
        document.getElementById('admin-view').classList.remove('hidden');
        loadRules();
    } else {
        alert("密码错误");
    }
}

async function uploadRules() {
    if(filesToUpload.length === 0) {
        alert("请先选择或拖拽文件！");
        return;
    }

    const formData = new FormData();
    for(let i=0; i<filesToUpload.length; i++) {
        formData.append('files', filesToUpload[i]);
    }

    const btn = document.querySelector('.bottom-btn');
    const originalText = btn.innerText;
    btn.innerText = "⏳ 处理中...";
    btn.disabled = true;

    try {
        const res = await fetch('/api/upload_rules', {
            method: 'POST',
            body: formData
        });
        const data = await res.json();
        alert(data.message);

        filesToUpload = [];
        updateFilePreview();
        loadRules();
    } catch (e) {
        alert("上传失败：" + e);
    } finally {
        btn.innerText = originalText;
        btn.disabled = false;
    }
}

async function loadRules() {
    const res = await fetch('/api/list_rules');
    const data = await res.json();
    const list = document.getElementById('rule-list');
    list.innerHTML = '';
    data.files.forEach(f => {
        list.innerHTML += `
            <li>
                <span>${f}</span>
                <button class="delete-btn" onclick="deleteRule('${f}')" title="删除">
                    <i class="fa-solid fa-trash"></i>
                </button>
            </li>
        `;
    });
}

async function deleteRule(filename) {
    if(!confirm(`确定要删除规则 "${filename}" 吗？`)) {
        return;
    }

    try {
        const res = await fetch('/api/delete_rule', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({filename: filename})
        });
        const data = await res.json();
        alert(data.message);
        loadRules();
    } catch (e) {
        alert("删除失败：" + e);
    }
}

// --- 拖拽上传逻辑 ---
document.addEventListener('DOMContentLoaded', () => {
    const dropArea = document.getElementById('drop-area');
    const fileInput = document.getElementById('rule-files');

    if(dropArea && fileInput) {
        // 点击盒子触发 Input
        dropArea.addEventListener('click', () => fileInput.click());

        // Input 变化
        fileInput.addEventListener('change', function() {
            handleFiles(this.files);
        });

        // 拖拽事件
        dropArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropArea.classList.add('highlight');
        });

        dropArea.addEventListener('dragleave', (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropArea.classList.remove('highlight');
        });

        dropArea.addEventListener('drop', (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropArea.classList.remove('highlight');
            handleFiles(e.dataTransfer.files);
        });
    }
});

function handleFiles(files) {
    filesToUpload = [...files];
    updateFilePreview();
}

function updateFilePreview() {
    const previewArea = document.getElementById('file-preview');
    previewArea.innerHTML = '';
    if(filesToUpload.length > 0) {
        filesToUpload.forEach(file => {
            previewArea.innerHTML += `
                <div class="file-tag">
                    <i class="fa-solid fa-file"></i> ${file.name}
                </div>
            `;
        });
    }
}
