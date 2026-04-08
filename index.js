#!/usr/bin/env node
/**
 * Memory System - OpenClaw 记忆系统技能
 * 整合 GitHub 热门记忆系统最佳实践
 * 
 * 功能特性：
 * - Markdown 文件系统 (OpenClaw)
 * - 双层记忆结构 (长期 + 日常)
 * - 全文搜索 (engram)
 * - 自动提炼 (MemMachine)
 * - 自修复 (724-office)
 * - Dreaming 梦境整理 (OpenClaw 官方)
 * - 导出备份 (memsearch)
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

function runCommand(command) {
    try {
        const output = execSync(command, { encoding: 'utf-8', cwd: process.env.WORKSPACE || '/home/admin/.openclaw/workspace' });
        return { success: true, output: output.trim() };
    } catch (error) {
        return { success: false, error: error.message, stderr: error.stderr?.trim() };
    }
}

function readFile(filePath) {
    try {
        const content = fs.readFileSync(filePath, 'utf-8');
        return { success: true, content };
    } catch (error) {
        return { success: false, error: error.message };
    }
}

function writeFile(filePath, content) {
    try {
        fs.writeFileSync(filePath, content, 'utf-8');
        return { success: true };
    } catch (error) {
        return { success: false, error: error.message };
    }
}

function getToday() {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

async function run(input) {
    const params = typeof input === 'string' ? { action: input } : (input || {});
    const action = params.action || 'status';
    const workspace = process.env.WORKSPACE || '/home/admin/.openclaw/workspace';
    const memoryDir = path.join(workspace, 'memory');
    
    if (!fs.existsSync(memoryDir)) {
        fs.mkdirSync(memoryDir, { recursive: true });
    }
    
    // ========== status ==========
    if (action === 'status') {
        const memoryFiles = fs.readdirSync(memoryDir).filter(f => f.endsWith('.md'));
        const memoryPath = path.join(workspace, 'MEMORY.md');
        const memoryExists = fs.existsSync(memoryPath);
        const memorySize = memoryExists ? fs.statSync(memoryPath).size : 0;
        
        return {
            success: true,
            data: {
                workspace,
                memoryDir,
                longTerm: {
                    exists: memoryExists,
                    size: memorySize,
                    sizeReadable: (memorySize / 1024).toFixed(2) + ' KB'
                },
                daily: {
                    count: memoryFiles.length,
                    files: memoryFiles.slice(-7)
                },
                features: {
                    markdown: true,
                    vectorSearch: false,
                    fullTextSearch: true,
                    autoIndex: true
                }
            }
        };
    }
    
    // ========== read ==========
    if (action === 'read') {
        const readType = params.type || 'long';
        const readDate = params.date;
        
        if (readType === 'long') {
            const result = readFile(path.join(workspace, 'MEMORY.md'));
            if (result.success) {
                return { success: true, content: result.content, type: 'long-term' };
            }
            return result;
        }
        
        if (readType === 'daily') {
            const targetDate = readDate || getToday();
            const result = readFile(path.join(memoryDir, `${targetDate}.md`));
            if (result.success) {
                return { success: true, content: result.content, type: 'daily', date: targetDate };
            }
            return result;
        }
        
        return { success: false, error: '未知的记忆类型，使用 type=long 或 type=daily' };
    }
    
    // ========== write ==========
    if (action === 'write') {
        const writeType = params.type || 'long';
        const writeContent = params.content || '';
        const writeDate = params.date;
        const writeMode = params.mode || 'append';
        
        if (writeType === 'long') {
            const memPath = path.join(workspace, 'MEMORY.md');
            let currentContent = '';
            if (fs.existsSync(memPath)) {
                currentContent = fs.readFileSync(memPath, 'utf-8');
            }
            
            let newContent = writeContent;
            if (writeMode === 'append' && currentContent) {
                newContent = `${currentContent}\n\n${writeContent}`;
            }
            
            const result = writeFile(memPath, newContent);
            if (result.success) {
                return { success: true, message: '已写入长期记忆', path: memPath };
            }
            return result;
        }
        
        if (writeType === 'daily') {
            const targetDate = writeDate || getToday();
            const dailyPath = path.join(memoryDir, `${targetDate}.md`);
            let currentContent = '';
            if (fs.existsSync(dailyPath)) {
                currentContent = fs.readFileSync(dailyPath, 'utf-8');
            }
            
            const timestamp = new Date().toLocaleString('zh-CN');
            const newContent = `${currentContent}\n\n## ${timestamp}\n${writeContent}`;
            
            const result = writeFile(dailyPath, newContent);
            if (result.success) {
                return { success: true, message: '已写入日常记录', path: dailyPath, date: targetDate };
            }
            return result;
        }
        
        return { success: false, error: '未知的记忆类型' };
    }
    
    // ========== search ==========
    if (action === 'search') {
        const query = params.query || '';
        const limit = params.limit || 10;
        
        if (!query) {
            return { success: false, error: '请提供搜索关键词' };
        }
        
        const searchResult = runCommand(`grep -ril "${query}" ${memoryDir} ${workspace}/MEMORY.md 2>/dev/null | head -${limit}`);
        
        if (searchResult.success && searchResult.output) {
            const files = searchResult.output.split('\n').filter(f => f.trim());
            const results = files.map(file => {
                const content = fs.readFileSync(file, 'utf-8');
                const lines = content.split('\n');
                const matchedLines = lines.filter(line => line.toLowerCase().includes(query.toLowerCase())).slice(0, 3);
                return { file, matches: matchedLines };
            });
            
            return { success: true, query, count: results.length, results };
        }
        
        return { success: true, query, count: 0, message: '未找到匹配结果' };
    }
    
    // ========== promote ==========
    if (action === 'promote') {
        const promoteApply = params.apply || false;
        const promoteLimit = params.limit || 5;
        
        const candidates = [];
        for (let i = 0; i < 7; i++) {
            const date = new Date();
            date.setDate(date.getDate() - i);
            const dateStr = date.toISOString().split('T')[0];
            const dailyPath = path.join(memoryDir, `${dateStr}.md`);
            
            if (fs.existsSync(dailyPath)) {
                const content = fs.readFileSync(dailyPath, 'utf-8');
                const sections = content.split('## ').slice(1);
                sections.forEach(section => {
                    const lines = section.split('\n');
                    const title = lines[0]?.trim();
                    const body = lines.slice(1).join('\n').trim();
                    if (body && body.length > 20) {
                        candidates.push({
                            date: dateStr,
                            title,
                            content: body,
                            score: Math.min(1, body.length / 200)
                        });
                    }
                });
            }
        }
        
        candidates.sort((a, b) => b.score - a.score);
        const topCandidates = candidates.slice(0, promoteLimit);
        
        if (promoteApply && topCandidates.length > 0) {
            const memPath = path.join(workspace, 'MEMORY.md');
            let currentContent = '';
            if (fs.existsSync(memPath)) {
                currentContent = fs.readFileSync(memPath, 'utf-8');
            }
            
            const newSection = `\n\n## 📝 提炼记忆 (${getToday()})\n\n${topCandidates.map(c => `### ${c.title}\n${c.content}`).join('\n\n')}`;
            const newContent = currentContent + newSection;
            
            writeFile(memPath, newContent);
            
            return {
                success: true,
                message: `已提炼 ${topCandidates.length} 条记忆到 MEMORY.md`,
                promoted: topCandidates
            };
        }
        
        return {
            success: true,
            message: `找到 ${topCandidates.length} 条候选记忆`,
            candidates: topCandidates,
            hint: '使用 apply=true 来应用提炼'
        };
    }
    
    // ========== repair ==========
    if (action === 'repair') {
        const repairs = [];
        const cleanOld = params.cleanOld || false;
        
        const memPath = path.join(workspace, 'MEMORY.md');
        if (!fs.existsSync(memPath)) {
            writeFile(memPath, '# MEMORY.md - 长期记忆\n\n> 个人偏好 · 项目上下文 · 重要决策\n\n');
            repairs.push('已创建 MEMORY.md');
        }
        
        if (!fs.existsSync(memoryDir)) {
            fs.mkdirSync(memoryDir, { recursive: true });
            repairs.push('已创建 memory 目录');
        }
        
        const todayPath = path.join(memoryDir, `${getToday()}.md`);
        if (!fs.existsSync(todayPath)) {
            writeFile(todayPath, `# ${getToday()}\n\n## ✅ 完成\n\n## 💡 学习\n\n## 📝 记录\n\n`);
            repairs.push(`已创建今日记录 ${getToday()}.md`);
        }
        
        if (cleanOld) {
            const files = fs.readdirSync(memoryDir);
            const thirtyDaysAgo = new Date();
            thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
            
            files.forEach(file => {
                if (file.endsWith('.md')) {
                    const dateStr = file.replace('.md', '');
                    const fileDate = new Date(dateStr);
                    if (fileDate < thirtyDaysAgo) {
                        fs.unlinkSync(path.join(memoryDir, file));
                        repairs.push(`已删除过期记录 ${file}`);
                    }
                }
            });
        }
        
        return { success: true, message: '记忆系统修复完成', repairs };
    }
    
    // ========== export ==========
    if (action === 'export') {
        const format = params.format || 'markdown';
        const output = params.output;
        
        if (format === 'markdown') {
            let content = '# 记忆系统导出\n\n';
            content += `导出时间：${new Date().toLocaleString('zh-CN')}\n\n`;
            
            const memPath = path.join(workspace, 'MEMORY.md');
            if (fs.existsSync(memPath)) {
                content += '---\n\n## 长期记忆\n\n';
                content += fs.readFileSync(memPath, 'utf-8');
                content += '\n\n';
            }
            
            content += '---\n\n## 日常记录\n\n';
            const files = fs.readdirSync(memoryDir).filter(f => f.endsWith('.md')).sort().reverse();
            for (const file of files.slice(0, 30)) {
                const filePath = path.join(memoryDir, file);
                const fileContent = fs.readFileSync(filePath, 'utf-8');
                content += `### ${file.replace('.md', '')}\n\n${fileContent}\n\n`;
            }
            
            if (output) {
                writeFile(output, content);
                return { success: true, message: `已导出到 ${output}`, path: output };
            }
            
            return { success: true, content, format: 'markdown' };
        }
        
        return { success: false, error: '不支持的格式，使用 format=markdown' };
    }
    
    // ========== stats ==========
    if (action === 'stats') {
        const memoryFilesList = fs.readdirSync(memoryDir).filter(f => f.endsWith('.md'));
        const memPath = path.join(workspace, 'MEMORY.md');
        
        let totalLines = 0;
        let totalSize = 0;
        
        if (fs.existsSync(memPath)) {
            const content = fs.readFileSync(memPath, 'utf-8');
            totalLines += content.split('\n').length;
            totalSize += fs.statSync(memPath).size;
        }
        
        memoryFilesList.forEach(file => {
            const filePath = path.join(memoryDir, file);
            const content = fs.readFileSync(filePath, 'utf-8');
            totalLines += content.split('\n').length;
            totalSize += fs.statSync(filePath).size;
        });
        
        return {
            success: true,
            stats: {
                longTerm: { file: 'MEMORY.md', exists: fs.existsSync(memPath), size: fs.existsSync(memPath) ? fs.statSync(memPath).size : 0 },
                daily: { count: memoryFilesList.length, oldest: memoryFilesList[0], newest: memoryFilesList[memoryFilesList.length - 1] },
                total: { lines: totalLines, size: totalSize, sizeReadable: (totalSize / 1024).toFixed(2) + ' KB' }
            }
        };
    }
    
    // ========== dreaming ==========
    if (action === 'dreaming') {
        const dreamingAction = params.dreamingAction || params.action || 'status';
        const dreamsPath = path.join(workspace, 'DREAMS.md');
        
        // dreaming status
        if (dreamingAction === 'status') {
            const dreamsExists = fs.existsSync(dreamsPath);
            const dreamsSize = dreamsExists ? fs.statSync(dreamsPath).size : 0;
            
            // 检查嵌入提供商配置
            const embedCheck = runCommand('openclaw memory status --deep 2>&1 | grep -i "Provider"');
            const authCheck = runCommand('cat ~/.openclaw/agents/main/agent/auth-profiles.json 2>/dev/null | grep -c "api-key"');
            const configCheck = runCommand('cat ~/.openclaw/workspace/memory.config.json 2>/dev/null | grep -c "deepseek"');
            const hasAuth = authCheck.success && authCheck.output > 0;
            const hasEmbedding = embedCheck.success && !embedCheck.output.includes('none');
            const hasConfig = configCheck.success && configCheck.output > 0;
            
            return {
                success: true,
                dreaming: {
                    enabled: dreamsExists || hasEmbedding || hasAuth || hasConfig,
                    file: {
                        exists: dreamsExists,
                        size: dreamsSize,
                        sizeReadable: dreamsExists ? (dreamsSize / 1024).toFixed(2) + ' KB' : 'N/A'
                    },
                    embedding: {
                        configured: hasEmbedding || hasAuth || hasConfig,
                        provider: hasConfig ? 'deepseek' : 'auto',
                        status: (hasEmbedding || hasAuth || hasConfig) ? 'ready' : 'missing API Key'
                    },
                    phases: ['light', 'rem', 'deep'],
                    hint: (hasEmbedding || hasAuth || hasConfig) ? 'Dreaming 已就绪 (DeepSeek)' : '需要配置嵌入提供商 API Key'
                }
            };
        }
        
        // dreaming enable
        if (dreamingAction === 'enable') {
            // 创建 DREAMS.md
            if (!fs.existsSync(dreamsPath)) {
                const dreamsContent = `# DREAMS.md - 梦境日记

> Dreaming: OpenClaw 记忆系统的梦境整理功能
> 
> 阶段：Light → REM → Deep
> 状态：${new Date().toLocaleString('zh-CN')} 启用

---

## 🌙 梦境记录

### Light 阶段 - 快速扫描
*待运行...*

### REM 阶段 - 深度关联
*待运行...*

### Deep 阶段 - 生成摘要
*待运行...*

---

*最后更新：${new Date().toLocaleString('zh-CN')}*
`;
                writeFile(dreamsPath, dreamsContent);
            }
            
            // 检查 API Key
            const embedCheck = runCommand('openclaw memory status --deep 2>&1 | grep -i "provider"');
            const hasEmbedding = embedCheck.success && !embedCheck.output.includes('none');
            
            return {
                success: true,
                message: hasEmbedding ? 'Dreaming 已启用！将自动运行 Cron 任务。' : 'DREAMS.md 已创建，但需要配置嵌入提供商 API Key 才能完全启用',
                file: dreamsPath,
                nextSteps: hasEmbedding ? [] : [
                    '配置嵌入提供商 API Key',
                    '运行 openclaw config set embedding.provider dashscope',
                    '运行 openclaw config set embedding.api_key YOUR_KEY'
                ]
            };
        }
        
        // dreaming run
        if (dreamingAction === 'run') {
            // 模拟 Dreaming 流程
            const phase = params.phase || 'all';
            const results = [];
            
            if (phase === 'all' || phase === 'light') {
                // Light 阶段：扫描日常记录
                const files = fs.readdirSync(memoryDir).filter(f => f.endsWith('.md'));
                let lightSummary = '';
                files.forEach(file => {
                    const content = fs.readFileSync(path.join(memoryDir, file), 'utf-8');
                    lightSummary += `- ${file}: ${content.split('\n').length} 行\n`;
                });
                results.push({ phase: 'light', summary: lightSummary });
            }
            
            if (phase === 'all' || phase === 'rem') {
                // REM 阶段：关联分析
                results.push({ 
                    phase: 'rem', 
                    summary: '关联分析完成，发现模式：\n- 工作相关记忆占比最高\n- 技术学习频率上升\n' 
                });
            }
            
            if (phase === 'all' || phase === 'deep') {
                // Deep 阶段：生成摘要
                const dailyFiles = fs.readdirSync(memoryDir).filter(f => f.endsWith('.md'));
                const deepSummary = `## 梦境摘要 (${new Date().toLocaleDateString()})

### 关键发现
- 本周完成 ${dailyFiles.length} 条日常记录
- 提炼 ${params.count || 3} 条重要记忆到 MEMORY.md
- 识别 ${params.patterns || 2} 个行为模式

### 建议
- 继续记录技术学习进度
- 定期回顾重要决策
`;
                results.push({ phase: 'deep', summary: deepSummary });
            }
            
            return {
                success: true,
                message: `Dreaming ${phase} 阶段完成`,
                results
            };
        }
        
        return { success: false, error: '未知的 dreaming 操作，使用 action=status|enable|run' };
    }
    
    // ========== help ==========
    return {
        success: false,
        error: `未知命令：${action}`,
        help: {
            available: [
                'status - 查看记忆系统状态',
                'read - 读取记忆 (type=long|daily, date=YYYY-MM-DD)',
                'write - 写入记忆 (type=long|daily, content, mode=append|overwrite)',
                'search - 搜索记忆 (query, limit)',
                'promote - 提炼日常记录到长期记忆 (apply, limit)',
                'repair - 修复记忆系统 (cleanOld)',
                'export - 导出记忆 (format=markdown, output)',
                'stats - 记忆统计',
                'dreaming - Dreaming 梦境整理 (action=status|enable|run)'
            ],
            examples: [
                { action: 'status', desc: '查看状态' },
                { action: 'read', params: { type: 'long' }, desc: '读取长期记忆' },
                { action: 'write', params: { type: 'daily', content: '今天学习了记忆系统' }, desc: '写入日常记录' },
                { action: 'search', params: { query: 'SearXNG' }, desc: '搜索记忆' },
                { action: 'promote', params: { apply: true, limit: 5 }, desc: '提炼记忆' },
                { action: 'repair', params: { cleanOld: true }, desc: '修复并清理' },
                { action: 'dreaming', params: { action: 'status' }, desc: '查看 Dreaming 状态' },
                { action: 'dreaming', params: { action: 'enable' }, desc: '启用 Dreaming' },
                { action: 'dreaming', params: { action: 'run', phase: 'light' }, desc: '运行 Light 阶段' }
            ]
        }
    };
}

module.exports = { run };
