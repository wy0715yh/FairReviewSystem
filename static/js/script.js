let selectedAuditFile = null;
let selectedBatchFiles = [];
let filesToUpload = [];
let latestReportHtml = '';
let latestReportText = '';

function escapeHtml(str) {
    return String(str || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function switchTab(panelId, triggerBtn) {
    document.querySelectorAll('.panel').forEach((p) => p.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach((b) => b.classList.remove('active'));

    const panel = document.getElementById(panelId);
    if (panel) panel.classList.add('active');

    if (triggerBtn) {
        triggerBtn.classList.add('active');
    } else {
        const btn = document.querySelector(`.nav-item[data-panel="${panelId}"]`);
        if (btn) btn.classList.add('active');
    }

    if (panelId === 'rules-panel') {
        loadRules();
        loadCustomRules();
    }
    if (panelId === 'report-panel') {
        reloadHistoryMini();
    }
    if (panelId === 'settings-panel') {
        loadSettings();
    }
}

function switchTabById(panelId) {
    switchTab(panelId, null);
}

function focusBatch() {
    const el = document.getElementById('batch-anchor');
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function batchFileKey(file) {
    return `${file.name}__${file.size}__${file.lastModified}`;
}

function renderBatchFiles() {
    const preview = document.getElementById('batch-file-preview');
    const countLabel = document.getElementById('batch-file-name-display');
    const clearBtn = document.getElementById('clear-batch-files-btn');
    if (!preview || !countLabel || !clearBtn) return;

    if (!selectedBatchFiles.length) {
        countLabel.innerText = '未选择文件';
        clearBtn.classList.add('hidden');
        preview.innerHTML = '<div class="placeholder-text">可多次选择文件，系统会累计加入本次批量任务。</div>';
        return;
    }

    countLabel.innerText = `已选择 ${selectedBatchFiles.length} 个文件`;
    clearBtn.classList.remove('hidden');
    preview.innerHTML = selectedBatchFiles
        .map(
            (f, i) => `<div class="file-tag batch-tag">
                <span><i class="fa-solid fa-file"></i> ${escapeHtml(f.name)}</span>
                <button class="delete-btn" onclick="removeBatchFile(${i})" title="移除"><i class="fa-solid fa-trash"></i></button>
            </div>`
        )
        .join('');
}

function removeBatchFile(index) {
    selectedBatchFiles = selectedBatchFiles.filter((_, i) => i !== index);
    renderBatchFiles();
}

function clearBatchFiles() {
    selectedBatchFiles = [];
    const input = document.getElementById('batch-files');
    if (input) input.value = '';
    renderBatchFiles();
}

function setLatestReport(html) {
    latestReportHtml = html || '';
    const tmp = document.createElement('div');
    tmp.innerHTML = latestReportHtml;
    latestReportText = tmp.textContent || tmp.innerText || '';

    const preview = document.getElementById('report-preview');
    if (preview) {
        preview.innerHTML = latestReportHtml || '<div class="placeholder-text">暂无报告</div>';
    }
}

function clearSelectedFile() {
    selectedAuditFile = null;
    const input = document.getElementById('audit-file');
    if (input) input.value = '';
    document.getElementById('file-name-display').innerText = '未选择文件';
    document.getElementById('clear-file-btn').classList.add('hidden');
}

async function startAudit() {
    const text = (document.getElementById('audit-text').value || '').trim();
    const resultBox = document.getElementById('audit-result');

    if (!text && !selectedAuditFile) {
        alert('请先输入文本或上传文件');
        return;
    }

    resultBox.innerHTML = '<div style="text-align:center; padding-top:50px;"><i class="fa-solid fa-spinner fa-spin fa-2x"></i><br><br>正在审查...</div>';

    const formData = new FormData();
    formData.append('text', text);
    if (selectedAuditFile) formData.append('file', selectedAuditFile);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 90000);

    try {
        const res = await fetch('/api/audit', { method: 'POST', body: formData, signal: controller.signal });
        const data = await res.json();

        if (!res.ok) {
            resultBox.innerText = data.error || data.message || `HTTP ${res.status}`;
            return;
        }
        resultBox.innerHTML = data.result || '无结果';
        setLatestReport(data.result || '');

        if (data.fallback) {
            const reason = data.error ? String(data.error) : '模型输出未结构化，已走系统兜底';
            resultBox.innerHTML += `<div class="warn-tip">提示：${escapeHtml(reason)}</div>`;
        }
    } catch (err) {
        if (err.name === 'AbortError') {
            resultBox.innerText = '请求超时，请稍后重试';
        } else {
            resultBox.innerText = '网络请求失败';
        }
    } finally {
        clearTimeout(timeoutId);
    }
}

async function startBatchAudit() {
    const textBlock = (document.getElementById('batch-texts').value || '').trim();
    const resultBox = document.getElementById('audit-result');

    if (!textBlock && selectedBatchFiles.length === 0) {
        alert('请提供批量文本或上传文件');
        return;
    }

    resultBox.innerHTML = '<div style="text-align:center; padding-top:50px;"><i class="fa-solid fa-spinner fa-spin fa-2x"></i><br><br>批量审查中...</div>';

    const fd = new FormData();
    if (textBlock) fd.append('texts', textBlock);
    selectedBatchFiles.forEach((f) => fd.append('files', f));

    try {
        const res = await fetch('/api/audit_batch', { method: 'POST', body: fd });
        const data = await res.json();
        if (!res.ok) {
            resultBox.innerText = data.error || data.message || `HTTP ${res.status}`;
            return;
        }
        resultBox.innerHTML = data.result || '无结果';
        setLatestReport(data.result || '');
    } catch (e) {
        resultBox.innerText = '批量审查失败';
    }
}

function resetCustomRuleForm() {
    document.getElementById('custom-rule-id').value = '';
    document.getElementById('custom-rule-name').value = '';
    document.getElementById('custom-rule-level').value = '中';
    document.getElementById('custom-rule-contract-type').value = '';
    document.getElementById('custom-rule-desc').value = '';
    document.getElementById('custom-rule-keywords').value = '';
}

async function saveCustomRule() {
    const id = document.getElementById('custom-rule-id').value.trim();
    const payload = {
        id: id || undefined,
        name: document.getElementById('custom-rule-name').value.trim(),
        risk_level: document.getElementById('custom-rule-level').value,
        contract_type: document.getElementById('custom-rule-contract-type').value.trim(),
        description: document.getElementById('custom-rule-desc').value.trim(),
        keywords: (document.getElementById('custom-rule-keywords').value || '')
            .split(',')
            .map((x) => x.trim())
            .filter(Boolean),
    };

    if (!payload.name) {
        alert('请填写规则名称');
        return;
    }

    try {
        const res = await fetch('/api/custom_rules', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (!res.ok) {
            alert(data.error || data.message || '保存失败');
            return;
        }
        resetCustomRuleForm();
        loadCustomRules();
    } catch (e) {
        alert('保存规则失败');
    }
}

async function loadCustomRules() {
    const list = document.getElementById('custom-rule-list');
    if (!list) return;

    try {
        const res = await fetch('/api/custom_rules');
        const data = await res.json();
        const rows = data.rules || [];
        if (!rows.length) {
            list.innerHTML = '<li><span>暂无自定义规则</span></li>';
            return;
        }

        list.innerHTML = rows
            .map((r) => {
                const json = encodeURIComponent(JSON.stringify(r));
                return `
                <li>
                    <span>
                        <b>${escapeHtml(r.name)}</b>（${escapeHtml(r.risk_level || '中')}）<br>
                        <small>${escapeHtml((r.keywords || []).join(', '))}</small>
                    </span>
                    <div>
                        <button class="delete-btn" onclick="editCustomRule('${json}')" title="编辑"><i class="fa-solid fa-pen"></i></button>
                        <button class="delete-btn" onclick="deleteCustomRule('${escapeHtml(r.id)}')" title="删除"><i class="fa-solid fa-trash"></i></button>
                    </div>
                </li>`;
            })
            .join('');
    } catch (e) {
        list.innerHTML = '<li><span>加载失败</span></li>';
    }
}

function editCustomRule(encoded) {
    try {
        const r = JSON.parse(decodeURIComponent(encoded));
        document.getElementById('custom-rule-id').value = r.id || '';
        document.getElementById('custom-rule-name').value = r.name || '';
        document.getElementById('custom-rule-level').value = r.risk_level || '中';
        document.getElementById('custom-rule-contract-type').value = r.contract_type || '';
        document.getElementById('custom-rule-desc').value = r.description || '';
        document.getElementById('custom-rule-keywords').value = (r.keywords || []).join(',');
    } catch (e) {
        alert('规则加载失败');
    }
}

async function deleteCustomRule(ruleId) {
    if (!confirm('确定删除该自定义规则吗？')) return;
    try {
        const res = await fetch(`/api/custom_rules/${encodeURIComponent(ruleId)}`, { method: 'DELETE' });
        const data = await res.json();
        if (!res.ok) {
            alert(data.error || data.message || '删除失败');
            return;
        }
        loadCustomRules();
    } catch (e) {
        alert('删除失败');
    }
}

async function uploadRules() {
    if (filesToUpload.length === 0) {
        alert('请先选择或拖拽文件');
        return;
    }
    const fd = new FormData();
    filesToUpload.forEach((f) => fd.append('files', f));

    try {
        const res = await fetch('/api/upload_rules', { method: 'POST', body: fd });
        const data = await res.json();
        alert(data.message || '完成');
        filesToUpload = [];
        updateFilePreview();
        loadRules();
    } catch (e) {
        alert('上传失败');
    }
}

async function loadRules() {
    const list = document.getElementById('rule-list');
    if (!list) return;
    try {
        const res = await fetch('/api/list_rules');
        const data = await res.json();
        const files = data.files || [];
        if (!files.length) {
            list.innerHTML = '<li><span>暂无规则库文件</span></li>';
            return;
        }
        list.innerHTML = files
            .map(
                (f) => `<li><span>${escapeHtml(f)}</span><button class="delete-btn" onclick="deleteRule('${escapeHtml(
                    f
                )}')"><i class="fa-solid fa-trash"></i></button></li>`
            )
            .join('');
    } catch (e) {
        list.innerHTML = '<li><span>加载失败</span></li>';
    }
}

async function deleteRule(filename) {
    if (!confirm(`确定要删除规则 "${filename}" 吗？`)) return;
    try {
        const res = await fetch('/api/delete_rule', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename }),
        });
        const data = await res.json();
        if (!res.ok) {
            alert(data.error || data.message || '删除失败');
            return;
        }
        loadRules();
    } catch (e) {
        alert('删除失败');
    }
}

async function searchKnowledge() {
    const q = (document.getElementById('knowledge-query').value || '').trim();
    const box = document.getElementById('knowledge-result');
    if (!q) {
        box.innerHTML = '<div class="placeholder-text">请输入关键词</div>';
        return;
    }

    box.innerHTML = '<div style="text-align:center; padding:30px;"><i class="fa-solid fa-spinner fa-spin"></i> 检索中...</div>';
    try {
        const res = await fetch(`/api/knowledge_search?q=${encodeURIComponent(q)}`);
        const data = await res.json();
        const items = data.items || [];
        if (!items.length) {
            box.innerHTML = '<div class="placeholder-text">未检索到结果</div>';
            return;
        }
        box.innerHTML = items
            .map(
                (it, idx) => `
                <div class="knowledge-item">
                    <h4>依据片段${idx + 1}｜${escapeHtml(it.source)}｜片段${escapeHtml(it.chunk_id)}｜相似度${Number(it.score || 0).toFixed(3)}</h4>
                    <p>${escapeHtml(it.text)}</p>
                </div>`
            )
            .join('');
    } catch (e) {
        box.innerHTML = '<div class="placeholder-text">检索失败</div>';
    }
}

async function loadSettings() {
    const speedEl = document.getElementById('setting-speed-mode');
    const highEl = document.getElementById('setting-high');
    const mediumEl = document.getElementById('setting-medium');
    const localEl = document.getElementById('setting-local');
    const retainEl = document.getElementById('setting-retain-days');
    if (!speedEl || !highEl || !mediumEl || !localEl || !retainEl) {
        return;
    }

    try {
        const res = await fetch('/api/settings');
        const data = await res.json();
        const s = data.settings || {};
        const rt = s.risk_threshold || {};

        speedEl.value = s.speed_mode || 'balanced';
        highEl.value = rt.high ?? 0.8;
        mediumEl.value = rt.medium ?? 0.5;
        localEl.value = String(Boolean(s.local_mode));
        retainEl.value = s.retain_days ?? 7;
    } catch (e) {
        // 页面未集成设置模块或接口临时异常时，避免初始化弹窗打断主流程
        console.warn('加载设置失败:', e);
    }
}

async function saveSettings() {
    const speedEl = document.getElementById('setting-speed-mode');
    const highEl = document.getElementById('setting-high');
    const mediumEl = document.getElementById('setting-medium');
    const localEl = document.getElementById('setting-local');
    const retainEl = document.getElementById('setting-retain-days');
    if (!speedEl || !highEl || !mediumEl || !localEl || !retainEl) {
        alert('当前页面未启用系统设置模块');
        return;
    }

    const payload = {
        speed_mode: speedEl.value,
        risk_threshold: {
            high: Number(highEl.value || 0.8),
            medium: Number(mediumEl.value || 0.5),
        },
        local_mode: localEl.value === 'true',
        retain_days: Number(retainEl.value || 7),
    };

    try {
        const res = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (!res.ok) {
            alert(data.error || data.message || '保存失败');
            return;
        }
        alert('设置已保存');
    } catch (e) {
        alert('保存设置失败');
    }
}

async function reloadHistoryMini() {
    const list = document.getElementById('history-mini-list');
    if (!list) return;

    try {
        const res = await fetch('/api/history');
        const data = await res.json();
        const rows = data.history || [];
        if (!rows.length) {
            list.innerHTML = '<li><span>暂无记录</span></li>';
            return;
        }

        list.innerHTML = rows
            .slice(0, 20)
            .map(
                (h) => `<li>
                    <span>${escapeHtml(h.title)}<br><small>${escapeHtml(h.time)}</small></span>
                    <div class="btn-row">
                        <button class="delete-btn" onclick="openHistoryDetail(${Number(h.id)})" title="查看"><i class="fa-solid fa-eye"></i></button>
                        <button class="delete-btn" onclick="deleteHistoryMini(${Number(h.id)})" title="删除"><i class="fa-solid fa-trash"></i></button>
                    </div>
                </li>`
            )
            .join('');
    } catch (e) {
        list.innerHTML = '<li><span>加载失败</span></li>';
    }
}

async function openHistoryDetail(id) {
    try {
        const res = await fetch(`/api/history/${id}`);
        const data = await res.json();
        if (!res.ok || !data.record) {
            alert(data.error || data.message || '读取失败');
            return;
        }
        setLatestReport(data.record.result || '');
        switchTabById('report-panel');
    } catch (e) {
        alert('读取失败');
    }
}

async function deleteHistoryMini(id) {
    if (!confirm('确定删除这条审查记录吗？')) return;
    try {
        const res = await fetch(`/api/history/${id}`, { method: 'DELETE' });
        const data = await res.json();
        if (!res.ok) {
            alert(data.error || data.message || '删除失败');
            return;
        }
        reloadHistoryMini();
    } catch (e) {
        alert('删除失败');
    }
}

async function clearHistoryMini() {
    if (!confirm('确定清空全部审查记录吗？此操作不可恢复。')) return;
    try {
        const res = await fetch('/api/history', { method: 'DELETE' });
        const data = await res.json();
        if (!res.ok) {
            alert(data.error || data.message || '清空失败');
            return;
        }
        reloadHistoryMini();
        const preview = document.getElementById('report-preview');
        if (preview) {
            preview.innerHTML = '<div class="placeholder-text">完成一次审查后，这里显示最新报告预览。</div>';
        }
        latestReportHtml = '';
        latestReportText = '';
    } catch (e) {
        alert('清空失败');
    }
}

function downloadFile(filename, content, mimeType) {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

async function exportByBackend(format) {
    if (!latestReportHtml) {
        alert('暂无可导出报告');
        return;
    }
    try {
        const res = await fetch('/api/export_report', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                format,
                title: `审查报告_${Date.now()}`,
                html: latestReportHtml,
            }),
        });
        if (!res.ok) {
            let msg = `导出失败（HTTP ${res.status}）`;
            try {
                const data = await res.json();
                if (data.error || data.message) msg = data.error || data.message;
            } catch (e) {}
            alert(msg);
            return;
        }
        const blob = await res.blob();
        const cd = res.headers.get('Content-Disposition') || '';
        const match = cd.match(/filename\*=UTF-8''([^;]+)|filename=\"?([^\";]+)\"?/i);
        let filename = `审查报告.${format}`;
        if (match) {
            filename = decodeURIComponent(match[1] || match[2]);
        }
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    } catch (e) {
        alert('导出失败');
    }
}

function exportLatestDocx() {
    exportByBackend('docx');
}

function exportLatestPdf() {
    exportByBackend('pdf');
}

function handleFiles(files) {
    filesToUpload = [...files];
    updateFilePreview();
}

function updateFilePreview() {
    const preview = document.getElementById('file-preview');
    if (!preview) return;
    if (filesToUpload.length === 0) {
        preview.innerHTML = '<div class="placeholder-text">未选择入库文件</div>';
        return;
    }
    preview.innerHTML = filesToUpload
        .map((f) => `<div class="file-tag"><i class="fa-solid fa-file"></i> ${escapeHtml(f.name)}</div>`)
        .join('');
}

function initFileInputs() {
    const single = document.getElementById('audit-file');
    if (single) {
        single.addEventListener('change', (e) => {
            selectedAuditFile = e.target.files && e.target.files[0] ? e.target.files[0] : null;
            document.getElementById('file-name-display').innerText = selectedAuditFile ? selectedAuditFile.name : '未选择文件';
            document.getElementById('clear-file-btn').classList.toggle('hidden', !selectedAuditFile);
        });
    }

    const batch = document.getElementById('batch-files');
    if (batch) {
        batch.addEventListener('change', (e) => {
            const incoming = [...(e.target.files || [])];
            if (incoming.length) {
                const seen = new Set(selectedBatchFiles.map(batchFileKey));
                incoming.forEach((f) => {
                    const k = batchFileKey(f);
                    if (!seen.has(k)) {
                        selectedBatchFiles.push(f);
                        seen.add(k);
                    }
                });
            }
            batch.value = '';
            renderBatchFiles();
        });
    }

    const dropArea = document.getElementById('drop-area');
    const fileInput = document.getElementById('rule-files');
    if (dropArea && fileInput) {
        dropArea.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', function () {
            handleFiles(this.files || []);
        });
        dropArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropArea.classList.add('highlight');
        });
        dropArea.addEventListener('dragleave', (e) => {
            e.preventDefault();
            dropArea.classList.remove('highlight');
        });
        dropArea.addEventListener('drop', (e) => {
            e.preventDefault();
            dropArea.classList.remove('highlight');
            handleFiles(e.dataTransfer.files || []);
        });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    initFileInputs();
    loadRules();
    loadCustomRules();
    loadSettings();
    reloadHistoryMini();
    updateFilePreview();
    renderBatchFiles();
});
