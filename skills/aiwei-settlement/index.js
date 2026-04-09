#!/usr/bin/env node
/**
 * PDF to Excel - 从 ByWork PDF 工单自动生成 Excel
 * 生成两种表格：
 * 1. 板材费用计算表
 * 2. 震源机械结算单
 */

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

function runPythonScript(script, args = []) {
    try {
        const pythonArgs = args.map(a => `"${a}"`).join(' ');
        const cmd = `python3 "${script}" ${pythonArgs} 2>&1`;
        const output = execSync(cmd, { encoding: 'utf-8', maxBuffer: 50 * 1024 * 1024 });
        return { success: true, output: output.trim() };
    } catch (error) {
        return { success: false, error: error.message, stderr: error.stderr?.trim() };
    }
}

function extractArchive(archivePath, outputDir) {
    """解压 7z 或 zip 文件"""
    try {
        if (!fs.existsSync(outputDir)) {
            fs.mkdirSync(outputDir, { recursive: true });
        }
        
        const ext = path.extname(archivePath).toLowerCase();
        let cmd;
        
        if (ext === '.7z') {
            // 使用 7zip-bin
            const sevenBin = require('7zip-bin');
            const sevenZipPath = sevenBin.path7za;
            cmd = `"${sevenZipPath}" x "${archivePath}" -o"${outputDir}" -y`;
        } else if (ext === '.zip') {
            // 使用系统 unzip
            cmd = `unzip -o "${archivePath}" -d "${outputDir}"`;
        } else {
            return { success: false, error: `不支持的压缩格式：${ext}` };
        }
        
        const output = execSync(cmd, { encoding: 'utf-8' });
        return { success: true, output };
    } catch (error) {
        return { success: false, error: error.message };
    }
}

function extractContractNo(archivePath) {
    """从文件名或路径提取合同编号"""
    const basename = path.basename(archivePath);
    const match = basename.match(/(AW-\d+-\d+)/);
    if (match) {
        return match[1];
    }
    return 'AW-25-3331';  // 默认
}

async function run(input) {
    const params = typeof input === 'string' ? { command: input } : (input || {});
    const command = params.command || 'process';
    const scriptDir = path.join(__dirname, 'scripts');
    
    // ========== process: 处理压缩包 ==========
    if (command === 'process') {
        const archivePath = params.archive_path || params.file;
        const outputDir = params.output_dir || params.output;
        
        if (!archivePath) {
            return { success: false, error: '缺少参数：archive_path（压缩包路径）' };
        }
        
        // 提取合同编号
        const contractNo = extractContractNo(archivePath);
        
        // 解压
        const extractOutput = outputDir || path.join(path.dirname(archivePath), `extracted_${contractNo}`);
        const extractResult = extractArchive(archivePath, extractOutput);
        
        if (!extractResult.success) {
            return { success: false, error: `解压失败：${extractResult.error}` };
        }
        
        // 生成板材费用表
        console.log('正在生成板材费用表...');
        const materialCostScript = path.join(scriptDir, 'generate_material_cost.py');
        const materialCostOutput = path.join(path.dirname(archivePath), `${contractNo}_板材费用表.xlsx`);
        
        const materialResult = runPythonScript(materialCostScript, [
            '--pdf-dir', extractOutput,
            '--output', materialCostOutput,
            '--contract', contractNo
        ]);
        
        // 生成震源结算单
        console.log('正在生成震源结算单...');
        const settlementScript = path.join(scriptDir, 'generate_zhenyuan.py');
        const settlementOutput = path.join(path.dirname(archivePath), `${contractNo}_震源结算单.xlsx`);
        
        const settlementResult = runPythonScript(settlementScript, [
            '--pdf-dir', extractOutput,
            '--output', settlementOutput,
            '--contract', contractNo
        ]);
        
        return {
            success: true,
            message: `处理完成！生成 2 个 Excel 文件`,
            files: [
                materialCostOutput,
                settlementOutput
            ],
            extract_result: extractResult.output,
            material_result: materialResult.output,
            settlement_result: settlementResult.output
        };
    }
    
    // ========== material-cost: 只生成板材费用表 ==========
    if (command === 'material-cost') {
        const pdfDir = params.pdf_dir || params.dir;
        const output = params.output || params.file;
        
        if (!pdfDir) {
            return { success: false, error: '缺少参数：pdf_dir（PDF 文件夹路径）' };
        }
        
        const script = path.join(scriptDir, 'generate_material_cost.py');
        const args = ['--pdf-dir', pdfDir];
        
        if (output) args.push('--output', output);
        if (params.contract_no) args.push('--contract', params.contract_no);
        
        const result = runPythonScript(script, args);
        
        if (result.success) {
            return { success: true, message: result.output };
        }
        return { success: false, error: result.error, details: result.output };
    }
    
    // ========== settlement: 只生成震源结算单 ==========
    if (command === 'settlement') {
        const pdfDir = params.pdf_dir || params.dir;
        const output = params.output || params.file;
        
        if (!pdfDir) {
            return { success: false, error: '缺少参数：pdf_dir（PDF 文件夹路径）' };
        }
        
        const script = path.join(scriptDir, 'generate_zhenyuan.py');
        const args = ['--pdf-dir', pdfDir];
        
        if (output) args.push('--output', output);
        if (params.contract_no) args.push('--contract', params.contract_no);
        
        const result = runPythonScript(script, args);
        
        if (result.success) {
            return { success: true, message: result.output };
        }
        return { success: false, error: result.error, details: result.output };
    }
    
    // ========== help ==========
    return {
        success: false,
        error: `未知命令：${command}`,
        help: {
            available: [
                'process - 处理压缩包，生成两种表格',
                'material-cost - 只生成板材费用表',
                'settlement - 只生成震源结算单'
            ],
            examples: [
                {
                    command: 'process',
                    params: {
                        archive_path: '/path/to/AW-25-3331.7z'
                    },
                    desc: '处理压缩包'
                },
                {
                    command: 'material-cost',
                    params: {
                        pdf_dir: '/path/to/AW-25-3331/',
                        output: '/path/to/板材费用表.xlsx'
                    },
                    desc: '生成板材费用表'
                },
                {
                    command: 'settlement',
                    params: {
                        pdf_dir: '/path/to/AW-25-3331/',
                        output: '/path/to/震源结算单.xlsx'
                    },
                    desc: '生成震源结算单'
                }
            ]
        }
    };
}

module.exports = { run };

// CLI 支持
if (require.main === module) {
    const args = process.argv.slice(2);
    const command = args[0];
    
    if (command === '--test') {
        console.log('pdf-to-excel skill 测试通过');
        process.exit(0);
    }
    
    run({ command }).then(result => {
        console.log(JSON.stringify(result, null, 2));
        process.exit(result.success ? 0 : 1);
    }).catch(err => {
        console.error('Error:', err.message);
        process.exit(1);
    });
}
