/* PARA Tracker - 前端逻辑 (Alpine.js) */

function app() {
    return {
        // Tab
        currentTab: 'tasks',

        // Status
        status: { ticktick: false, flomo: false, ai_summary: false },
        syncing: false,

        // Tasks
        tasks: [],
        taskFilter: 'all',
        pendingTasks: [],
        todayCompleted: [],

        // New Task Modal
        showNewTaskModal: false,
        newTask: {
            title: '',
            priority: 0,
            due_date: '',
            tags: [],
        },
        newTaskTagInput: '',
        newTaskTagSearchResults: [],
        newTaskTagSelectedIndex: -1,
        recentTags: [],
        showTagSuggestions: false,

        // Memos
        memos: [],
        recentMemos: [],

        // PARA
        paraTree: [],
        showAddParaTag: false,
        newTagCategory: '01-Projects',
        newTagLabel: '',

        // Edit PARA Tag
        showEditParaTag: false,
        editParaTagId: null,
        editParaTagLabel: '',
        editParaTagFullPath: '',

        // Daily Summary
        todaySummary: null,
        summaryLoading: false,

        // Edit Task Modal
        showEditTaskModal: false,
        editTask: {
            id: null,
            title: '',
            content: '',
            priority: 0,
            due_date: '',
            tags: [],
        },
        editTaskTagInput: '',
        editTaskTagSearchResults: [],
        editTaskTagSelectedIndex: -1,

        // Note Modal (task completion)
        showNoteModal: false,
        completingTask: null,
        noteContent: '',
        suggestedTags: [],
        selectedTags: [],

        // Edit Memo Modal
        showEditMemoModal: false,
        editMemoId: null,
        editMemoContent: '',
        editMemoTags: [],
        editMemoTagInput: '',
        editMemoTagSearchResults: [],
        editMemoTagSelectedIndex: -1,

        // Free Note Modal
        showFreeNoteModal: false,
        freeNoteContent: '',
        freeNoteTag: '',

        // Config
        config: {
            ticktick_username: '',
            ticktick_password: '',
            flomo_api_url: '',
            openai_api_key: '',
            openai_base_url: 'https://api.openai.com/v1',
        },

        async init() {
            this.checkStatus();
            this.loadParaTree();
            this.loadData();
        },

        // ====== API 调用 ======
        async api(method, path, body = null) {
            const opts = {
                method,
                headers: { 'Content-Type': 'application/json' },
            };
            if (body) opts.body = JSON.stringify(body);
            const resp = await fetch(path, opts);
            if (!resp.ok) {
                const err = await resp.json().catch(() => ({ detail: resp.statusText }));
                throw new Error(err.detail || '请求失败');
            }
            return resp.json();
        },

        // ====== 状态检查 ======
        async checkStatus() {
            try {
                const data = await this.api('GET', '/api/sync/status');
                this.status = data;
            } catch (e) {
                console.warn('状态检查失败:', e);
            }
        },

        // ====== 数据加载 ======
        async loadData() {
            await Promise.all([
                this.loadTasks(),
                this.loadMemos(),
                this.loadSummary(),
            ]);
        },

        async loadTasks() {
            try {
                const params = this.taskFilter !== 'all' ? `?status=${this.taskFilter}` : '';
                this.tasks = await this.api('GET', `/api/tasks${params}`);

                this.pendingTasks = this.tasks.filter(t => t.status === 'todo');
                const today = new Date().toISOString().split('T')[0];
                this.todayCompleted = this.tasks.filter(t => {
                    if (t.status !== 'done' || !t.completed_at) return false;
                    return t.completed_at.startsWith(today);
                });
            } catch (e) {
                console.warn('加载任务失败:', e);
            }
        },

        getCategory(tags) {
            if (!tags || tags.length === 0) return '其他';
            for (const tag of tags) {
                if (tag.startsWith('01-')) return '01-Projects';
                if (tag.startsWith('02-')) return '02-Areas';
                if (tag.startsWith('03-')) return '03-Resources';
                if (tag.startsWith('04-')) return '04-Archives';
            }
            return '其他';
        },

        get groupedTasks() {
            const groups = { '01-Projects': [], '02-Areas': [], '03-Resources': [], '04-Archives': [], '其他': [] };
            for (const t of this.tasks) {
                const cat = this.getCategory(t.tags);
                groups[cat].push(t);
            }
            return groups;
        },

        get groupedMemos() {
            const groups = { '01-Projects': [], '02-Areas': [], '03-Resources': [], '04-Archives': [], '其他': [] };
            for (const m of this.memos) {
                const cat = this.getCategory(m.tags);
                groups[cat].push(m);
            }
            return groups;
        },

        async loadMemos() {
            try {
                this.memos = await this.api('GET', '/api/memos');
                this.recentMemos = this.memos.slice(0, 5);
            } catch (e) {
                console.warn('加载笔记失败:', e);
            }
        },

        async loadSummary() {
            try {
                this.todaySummary = await this.api('GET', '/api/summary/today');
            } catch (e) {
                console.warn('加载总结失败:', e);
            }
        },

        async loadParaTree() {
            try {
                this.paraTree = await this.api('GET', '/api/para/tags');
            } catch (e) {
                console.warn('加载标签树失败:', e);
            }
        },

        // ====== 同步 ======
        async syncData() {
            this.syncing = true;
            try {
                const result = await this.api('POST', '/api/sync/run');
                await this.loadData();
                alert(`同步完成! 项目: ${result.results?.projects || 0}, 任务: ${result.results?.tasks || 0}`);
            } catch (e) {
                alert('同步失败: ' + e.message);
            } finally {
                this.syncing = false;
            }
        },

        // ====== 切换任务状态 ======
        async toggleTask(task) {
            try {
                const result = await this.api('POST', `/api/tasks/${task.id}/toggle`);
                if (result.action === 'completed') {
                    this.completingTask = task;
                    this.suggestedTags = result.suggested_tags || [];
                    this.selectedTags = [...this.suggestedTags];
                    this.noteContent = '';
                    this.showNoteModal = true;
                }
                await this.loadTasks();
            } catch (e) {
                alert('操作失败: ' + e.message);
            }
        },

        // ====== 最近标签 ======
        async loadRecentTags() {
            try {
                this.recentTags = await this.api('GET', '/api/tasks/recent-tags');
            } catch (e) {
                console.warn('加载最近标签失败:', e);
            }
        },

        selectRecentTag(tag) {
            if (tag && !this.newTask.tags.includes(tag)) {
                this.newTask.tags.push(tag);
            }
            this.newTaskTagInput = '';
            this.showTagSuggestions = false;
        },

        // ====== 标签自动补全 ======
        async searchParaTags(input, resultProp, indexProp) {
            const q = input.trim();
            if (!q) {
                this[resultProp] = [];
                this[indexProp] = -1;
                return;
            }
            try {
                const results = await this.api('GET', `/api/para/tags/search?q=${encodeURIComponent(q)}`);
                this[resultProp] = results.map(r => r.full_path).filter(t => !this.newTask.tags.includes(t));
                this[indexProp] = this[resultProp].length > 0 ? 0 : -1;
            } catch (e) {
                this[resultProp] = [];
                this[indexProp] = -1;
            }
        },

        onNewTagInputKeydown(e) {
            const results = this.newTaskTagSearchResults;
            if (e.key === 'Tab' && results.length > 0) {
                e.preventDefault();
                this.newTaskTagInput = results[this.newTaskTagSelectedIndex];
                this.newTaskTagSearchResults = [];
                this.newTaskTagSelectedIndex = -1;
                this.addNewTaskTag();
            } else if (e.key === 'ArrowDown') {
                e.preventDefault();
                this.newTaskTagSelectedIndex = Math.min(this.newTaskTagSelectedIndex + 1, results.length - 1);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                this.newTaskTagSelectedIndex = Math.max(this.newTaskTagSelectedIndex - 1, 0);
            } else if (e.key === 'Escape') {
                this.newTaskTagSearchResults = [];
                this.newTaskTagSelectedIndex = -1;
            }
        },

        selectNewTagSuggestion(tag) {
            this.newTaskTagInput = tag;
            this.newTaskTagSearchResults = [];
            this.newTaskTagSelectedIndex = -1;
            this.addNewTaskTag();
        },

        onEditTagInputKeydown(e) {
            const results = this.editTaskTagSearchResults;
            if (e.key === 'Tab' && results.length > 0) {
                e.preventDefault();
                this.editTaskTagInput = results[this.editTaskTagSelectedIndex];
                this.editTaskTagSearchResults = [];
                this.editTaskTagSelectedIndex = -1;
                this.addEditTaskTag();
            } else if (e.key === 'ArrowDown') {
                e.preventDefault();
                this.editTaskTagSelectedIndex = Math.min(this.editTaskTagSelectedIndex + 1, results.length - 1);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                this.editTaskTagSelectedIndex = Math.max(this.editTaskTagSelectedIndex - 1, 0);
            } else if (e.key === 'Escape') {
                this.editTaskTagSearchResults = [];
                this.editTaskTagSelectedIndex = -1;
            }
        },

        selectEditTagSuggestion(tag) {
            this.editTaskTagInput = tag;
            this.editTaskTagSearchResults = [];
            this.editTaskTagSelectedIndex = -1;
            this.addEditTaskTag();
        },

        // ====== 新建任务 ======
        openNewTask() {
            this.newTask = { title: '', priority: 0, due_date: '', tags: [] };
            this.newTaskTagInput = '';
            this.showTagSuggestions = false;
            this.recentTags = [];
            this.showNewTaskModal = true;
            this.loadRecentTags();
        },

        addNewTaskTag() {
            const tag = this.newTaskTagInput.trim();
            if (tag && !this.newTask.tags.includes(tag)) {
                this.newTask.tags.push(tag);
            }
            this.newTaskTagInput = '';
        },

        removeNewTaskTag(tag) {
            this.newTask.tags = this.newTask.tags.filter(t => t !== tag);
        },

        async createNewTask() {
            if (!this.newTask.title.trim()) return;
            try {
                const priorityMap = { 'low': 1, 'medium': 3, 'high': 5 };
                const priority = priorityMap[this.newTask.priority] || 0;
                const dueDate = this.newTask.due_date
                    ? new Date(this.newTask.due_date).toISOString()
                    : null;
                await this.api('POST', '/api/tasks', {
                    title: this.newTask.title.trim(),
                    priority: priority,
                    due_date: dueDate,
                    tags: this.newTask.tags,
                });
                this.showNewTaskModal = false;
                await this.loadTasks();
            } catch (e) {
                alert('创建失败: ' + e.message);
            }
        },

        // ====== 编辑任务 ======
        openEditTask(task) {

            this.editTask = {
                id: task.id,
                title: task.title,
                content: task.content || '',
                priority: task.priority || 0,
                due_date: task.due_date ? task.due_date.split('T')[0] : '',
                tags: [...(task.tags || [])],
            };
            this.editTaskTagInput = '';
            this.showEditTaskModal = true;
        },

        addEditTaskTag() {
            const tag = this.editTaskTagInput.trim();
            if (tag && !this.editTask.tags.includes(tag)) {
                this.editTask.tags.push(tag);
            }
            this.editTaskTagInput = '';
        },

        removeEditTaskTag(tag) {
            this.editTask.tags = this.editTask.tags.filter(t => t !== tag);
        },

        async saveEditTask() {
            if (!this.editTask.title.trim()) return;
            try {
                const dueDate = this.editTask.due_date
                    ? new Date(this.editTask.due_date).toISOString()
                    : null;
                await this.api('PUT', `/api/tasks/${this.editTask.id}`, {
                    title: this.editTask.title.trim(),
                    content: this.editTask.content,
                    priority: parseInt(this.editTask.priority) || 0,
                    due_date: dueDate,
                    tags: this.editTask.tags,
                });
                this.showEditTaskModal = false;
                await this.loadTasks();
            } catch (e) {
                alert('保存失败: ' + e.message);
            }
        },

        async deleteTask(task) {
            if (!confirm('确定删除任务「' + task.title + '」？')) return;
            try {
                await this.api('DELETE', `/api/tasks/${task.id}`);
                await this.loadTasks();
            } catch (e) {
                alert('删除失败: ' + e.message);
            }
        },

        // ====== 标签选择 ======
        toggleTag(tag) {
            const idx = this.selectedTags.indexOf(tag);
            if (idx >= 0) {
                this.selectedTags.splice(idx, 1);
            } else {
                this.selectedTags.push(tag);
            }
        },

        // ====== 保存任务完成笔记 ======
        async saveTaskMemo() {
            try {
                await this.api('POST', '/api/memos/from-task', {
                    content: this.noteContent,
                    tags: this.selectedTags,
                    task_id: this.completingTask.id,
                });
                this.showNoteModal = false;
                this.noteContent = '';
                await this.loadMemos();
            } catch (e) {
                alert('保存失败: ' + e.message);
            }
        },

        // ====== 编辑笔记 ======
        openEditMemo(memo) {
            this.editMemoId = memo.id;
            this.editMemoContent = memo.content;
            this.editMemoTags = [...(memo.tags || [])];
            this.editMemoTagInput = '';
            this.editMemoTagSearchResults = [];
            this.editMemoTagSelectedIndex = -1;
            this.showEditMemoModal = true;
        },

        async saveEditMemo() {
            if (!this.editMemoContent.trim()) return;
            try {
                await this.api('PUT', `/api/memos/${this.editMemoId}`, {
                    content: this.editMemoContent.trim(),
                    tags: this.editMemoTags,
                });
                this.showEditMemoModal = false;
                await this.loadMemos();
            } catch (e) {
                alert('保存失败: ' + e.message);
            }
        },

        async deleteMemo(memo) {
            if (!confirm('确定删除这条笔记？')) return;
            try {
                await this.api('DELETE', `/api/memos/${memo.id}`);
                await this.loadMemos();
            } catch (e) {
                alert('删除失败: ' + e.message);
            }
        },

        addEditMemoTag() {
            const tag = this.editMemoTagInput.trim();
            if (tag && !this.editMemoTags.includes(tag)) {
                this.editMemoTags.push(tag);
            }
            this.editMemoTagInput = '';
        },

        removeEditMemoTag(tag) {
            this.editMemoTags = this.editMemoTags.filter(t => t !== tag);
        },

        searchEditMemoTags() {
            const q = this.editMemoTagInput.trim();
            if (!q) {
                this.editMemoTagSearchResults = [];
                this.editMemoTagSelectedIndex = -1;
                return;
            }
            this.api('GET', `/api/para/tags/search?q=${encodeURIComponent(q)}`).then(results => {
                this.editMemoTagSearchResults = results.map(r => r.full_path).filter(t => !this.editMemoTags.includes(t));
                this.editMemoTagSelectedIndex = this.editMemoTagSearchResults.length > 0 ? 0 : -1;
            }).catch(() => {
                this.editMemoTagSearchResults = [];
                this.editMemoTagSelectedIndex = -1;
            });
        },

        onEditMemoTagKeydown(e) {
            const results = this.editMemoTagSearchResults;
            if (e.key === 'Tab' && results.length > 0) {
                e.preventDefault();
                this.editMemoTagInput = results[this.editMemoTagSelectedIndex];
                this.editMemoTagSearchResults = [];
                this.editMemoTagSelectedIndex = -1;
                this.addEditMemoTag();
            } else if (e.key === 'ArrowDown') {
                e.preventDefault();
                this.editMemoTagSelectedIndex = Math.min(this.editMemoTagSelectedIndex + 1, results.length - 1);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                this.editMemoTagSelectedIndex = Math.max(this.editMemoTagSelectedIndex - 1, 0);
            } else if (e.key === 'Escape') {
                this.editMemoTagSearchResults = [];
                this.editMemoTagSelectedIndex = -1;
            }
        },

        selectEditMemoTagSuggestion(tag) {
            this.editMemoTagInput = tag;
            this.editMemoTagSearchResults = [];
            this.editMemoTagSelectedIndex = -1;
            this.addEditMemoTag();
        },

        // ====== 自由笔记 ======
        openFreeNote() {
            this.freeNoteContent = '';
            this.freeNoteTag = '';
            this.showFreeNoteModal = true;
        },

        async saveFreeNote() {
            try {
                const tags = this.freeNoteTag ? [this.freeNoteTag] : [];
                await this.api('POST', '/api/memos', {
                    content: this.freeNoteContent,
                    tags: tags,
                    source: 'free_write',
                });
                this.showFreeNoteModal = false;
                this.freeNoteContent = '';
                await this.loadMemos();
            } catch (e) {
                alert('保存失败: ' + e.message);
            }
        },

        // ====== 每日总结 ======
        async generateSummary() {
            this.summaryLoading = true;
            try {
                const result = await this.api('POST', '/api/summary/generate');
                if (result.summary) {
                    this.todaySummary = {
                        has_summary: true,
                        summary_text: result.summary.summary_text,
                        suggestions: result.summary.suggestions || [],
                        completed_tasks: [],
                        memos: [],
                    };
                } else {
                    alert(result.message || '暂无数据可总结');
                }
            } catch (e) {
                alert('生成总结失败: ' + e.message);
            } finally {
                this.summaryLoading = false;
            }
        },

        // ====== PARA 标签管理 ======
        async createParaTag() {
            if (!this.newTagLabel.trim()) return;
            try {
                const fullPath = this.newTagCategory + '/' + this.newTagLabel.trim();
                await this.api('POST', '/api/para/tags', { full_path: fullPath });
                this.newTagLabel = '';
                this.showAddParaTag = false;
                await this.loadParaTree();
            } catch (e) {
                alert('创建标签失败: ' + e.message);
            }
        },

        async deleteParaTag(tagId) {
            if (!confirm('确定删除此标签？')) return;
            try {
                await this.api('DELETE', `/api/para/tags/${tagId}`);
                await this.loadParaTree();
            } catch (e) {
                alert('删除失败: ' + e.message);
            }
        },

        openEditParaTag(tag) {
            this.editParaTagId = tag.id;
            this.editParaTagLabel = tag.label;
            this.editParaTagFullPath = tag.full_path;
            this.showEditParaTag = true;
        },

        async saveEditParaTag() {
            if (!this.editParaTagLabel.trim()) return;
            try {
                await this.api('PUT', `/api/para/tags/${this.editParaTagId}`, {
                    label: this.editParaTagLabel.trim(),
                });
                this.showEditParaTag = false;
                await this.loadParaTree();
            } catch (e) {
                alert('保存失败: ' + e.message);
            }
        },

        // ====== 配置保存 ======
        async saveTickTick() {
            try {
                // 优先使用密码方式登录（简单模式）
                if (this.config.ticktick_username && this.config.ticktick_password) {
                    await this.api('POST', '/api/auth/ticktick/password', {
                        username: this.config.ticktick_username,
                        password: this.config.ticktick_password,
                    });
                } else {
                    alert('请输入 TickTick 用户名和密码');
                    return;
                }
                this.status.ticktick = true;
                alert('TickTick 配置成功!');
                await this.syncData();
            } catch (e) {
                alert('配置失败: ' + e.message);
            }
        },

        async saveFlomo() {
            try {
                await this.api('POST', '/api/auth/flomo', {
                    api_url: this.config.flomo_api_url,
                });
                this.status.flomo = true;
                alert('Flomo 配置成功!');
            } catch (e) {
                alert('配置失败: ' + e.message);
            }
        },

        async saveAI() {
            try {
                await this.api('POST', '/api/auth/ai', {
                    api_key: this.config.openai_api_key,
                    api_base: this.config.openai_base_url,
                    model: 'gpt-4o-mini',
                });
                this.status.ai_summary = true;
                alert('AI 配置成功!');
            } catch (e) {
                alert('配置失败: ' + e.message);
            }
        },

        // ====== 工具函数 ======
        categoryColor(cat) {
            const map = {
                '01-Projects': '#6366f1',
                '02-Areas': '#10b981',
                '03-Resources': '#f59e0b',
                '04-Archives': '#6b7280',
            };
            return map[cat] || '#6366f1';
        },

        // 从标签全路径中提取颜色类名 (p/a/r/arch)
        tagColor(tag) {
            if (tag.startsWith('01-')) return 'p';
            if (tag.startsWith('02-')) return 'a';
            if (tag.startsWith('03-')) return 'r';
            if (tag.startsWith('04-')) return 'arch';
            return 'p';
        },

        formatDate(d) {
            if (!d) return '';
            return new Date(d).toLocaleDateString('zh-CN');
        },

        formatTime(d) {
            if (!d) return '';
            const date = new Date(d);
            const now = new Date();
            const diff = now - date;
            if (diff < 60000) return '刚刚';
            if (diff < 3600000) return Math.floor(diff / 60000) + '分钟前';
            if (diff < 86400000) return Math.floor(diff / 3600000) + '小时前';
            return date.toLocaleDateString('zh-CN') + ' ' + date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
        },

        getMemoTitle(content) {
            if (!content) return '';
            const match = content.match(/^## (.+?)(?:\n|$)/);
            return match ? match[1] : '';
        },

        getMemoBody(content) {
            if (!content) return '';
            const idx = content.indexOf('\n\n');
            return idx >= 0 ? content.slice(idx + 2) : content;
        },

        renderMarkdown(text) {
            if (!text) return '';
            let html = text
                .replace(/### (.+)/g, '<h3>$1</h3>')
                .replace(/## (.+)/g, '<h2>$1</h2>')
                .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
                .replace(/\n/g, '<br>');
            return html;
        },
    };
}
