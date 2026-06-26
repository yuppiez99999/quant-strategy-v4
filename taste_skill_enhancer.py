"""
Taste Skill 前端设计增强模块 - 用于量化策略系统 v5.0

使用 Taste Skill Agent Skills 提升报告界面的视觉质量
支持生成专业级 HTML 报告，避免平庸的 AI 生成界面

安装方式:
    npx skills add https://github.com/Leonxlnx/taste-skill --skill "design-taste-frontend"

使用方法:
    from taste_skill_enhancer import TasteSkillReportEnhancer
    
    enhancer = TasteSkillReportEnhancer()
    html_report = enhancer.enhance_markdown_to_html(markdown_content, title="投资组合优化报告")
    enhancer.save_html(html_report, "report.html")
"""

import os
from datetime import datetime
from typing import Optional


class TasteSkillReportEnhancer:
    """
    使用 Taste Skill 规则增强报告视觉效果
    
    核心原则:
    - 更强的布局、排版、动效和间距
    - 避免 boilerplate-looking UIs
    - 应用高端视觉设计原则
    """
    
    def __init__(self, variance=7, motion=5, density=4):
        """
        初始化 Taste Skill 增强器
        
        Args:
            variance: 布局实验性 (1-10, 低=居中简洁, 高=不对称现代)
            motion: 动画深度 (1-10, 低=悬停效果, 高=滚动/磁性)
            density: 信息密度 (1-10, 低=宽敞, 高=密集仪表盘)
        """
        self.variance = variance
        self.motion = motion
        self.density = density
    
    def enhance_markdown_to_html(self, markdown_content: str, title: str = "量化策略报告", 
                                  save_path: Optional[str] = None) -> str:
        """
        将 Markdown 内容转换为精美的 HTML 报告
        
        应用 Taste Skill 设计原则:
        - 瑞士风格排版 (Swiss typography)
        - 充足的留白 (generous whitespace)
        - 清晰的视觉层次 (clear hierarchy)
        - 柔和的色彩对比 (soft contrast)
        - 弹簧动画效果 (spring motion)
        
        Args:
            markdown_content: Markdown 格式的报告内容
            title: 报告标题
            save_path: 可选的保存路径
            
        Returns:
            HTML 字符串
        """
        # 转换 Markdown 为结构化 HTML
        html_content = self._markdown_to_structured_html(markdown_content, title)
        
        # 应用 Taste Skill 样式
        styled_html = self._apply_taste_styles(html_content)
        
        if save_path:
            self.save_html(styled_html, save_path)
        
        return styled_html
    
    def _markdown_to_structured_html(self, markdown: str, title: str) -> str:
        """简单的 Markdown 到 HTML 转换"""
        lines = markdown.split('\n')
        html_parts = []
        
        for line in lines:
            line = line.strip()
            
            if not line:
                continue
            
            # 标题处理
            if line.startswith('=') * 10:
                continue  # 跳过分隔线
            
            elif line.startswith('📊') or line.startswith('🏆'):
                # 主要标题
                html_parts.append(f'<h1 class="main-title">{line}</h1>')
            
            elif line.startswith('📋') or line.startswith('📈'):
                # 二级标题
                html_parts.append(f'<h2 class="section-title">{line}</h2>')
            
            elif line.startswith('  ') and ':' in line:
                # 数据项
                key, value = line.strip().split(':', 1)
                html_parts.append(f'<div class="data-item"><span class="label">{key}:</span><span class="value">{value.strip()}</span></div>')
            
            elif line.startswith('✅') or line.startswith('❌'):
                # 状态指示
                html_parts.append(f'<div class="status-indicator">{line}</div>')
            
            else:
                # 普通文本
                html_parts.append(f'<p>{line}</p>')
        
        return '\n'.join(html_parts)
    
    def _apply_taste_styles(self, body_content: str) -> str:
        """应用 Taste Skill 设计风格"""
        
        # 根据配置参数选择配色方案
        color_scheme = self._get_color_scheme()
        
        html_template = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>量化策略报告</title>
    <style>
        /* ============================================
           Taste Skill Design System
           Anti-slop Frontend Framework
           ============================================ */
        
        :root {{
            /* 主色调 - 根据配置动态调整 */
            --primary: {color_scheme['primary']};
            --secondary: {color_scheme['secondary']};
            --accent: {color_scheme['accent']};
            
            /* 中性色 */
            --bg-primary: #fafafa;
            --bg-secondary: #ffffff;
            --text-primary: #1a1a1a;
            --text-secondary: #666666;
            --border: #e5e5e5;
            
            /* 间距系统 */
            --space-xs: 0.5rem;
            --space-sm: 1rem;
            --space-md: 1.5rem;
            --space-lg: 2.5rem;
            --space-xl: 4rem;
            
            /* 字体 */
            --font-sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            --font-mono: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, monospace;
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: var(--font-sans);
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: var(--space-xl) var(--space-lg);
        }}
        
        /* 主标题 - 瑞士风格排版 */
        .main-title {{
            font-size: clamp(2rem, 5vw, 3.5rem);
            font-weight: 700;
            letter-spacing: -0.02em;
            line-height: 1.1;
            margin-bottom: var(--space-lg);
            color: var(--text-primary);
            border-left: 4px solid var(--primary);
            padding-left: var(--space-md);
        }}
        
        /* 章节标题 */
        .section-title {{
            font-size: 1.5rem;
            font-weight: 600;
            margin-top: var(--space-xl);
            margin-bottom: var(--space-md);
            color: var(--text-primary);
            display: flex;
            align-items: center;
            gap: var(--space-sm);
        }}
        
        .section-title::before {{
            content: '';
            display: inline-block;
            width: 8px;
            height: 8px;
            background: var(--primary);
            border-radius: 50%;
        }}
        
        /* 数据项卡片 */
        .data-item {{
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: var(--space-md);
            margin-bottom: var(--space-sm);
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        }}
        
        .data-item:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
            border-color: var(--primary);
        }}
        
        .data-item .label {{
            font-weight: 500;
            color: var(--text-secondary);
            font-size: 0.95rem;
        }}
        
        .data-item .value {{
            font-weight: 600;
            color: var(--text-primary);
            font-family: var(--font-mono);
            font-size: 1.1rem;
        }}
        
        /* 状态指示器 */
        .status-indicator {{
            padding: var(--space-sm) var(--space-md);
            border-radius: 6px;
            font-weight: 500;
            margin: var(--space-xs) 0;
            display: inline-block;
        }}
        
        .status-indicator:contains('✅') {{
            background: rgba(16, 185, 129, 0.1);
            color: #059669;
        }}
        
        .status-indicator:contains('❌') {{
            background: rgba(239, 68, 68, 0.1);
            color: #dc2626;
        }}
        
        /* 响应式设计 */
        @media (max-width: 768px) {{
            .container {{
                padding: var(--space-lg) var(--space-md);
            }}
            
            .main-title {{
                font-size: 2rem;
            }}
        }}
        
        /* 打印优化 */
        @media print {{
            body {{
                background: white;
            }}
            
            .data-item {{
                break-inside: avoid;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        {body_content}
    </div>
</body>
</html>"""
        
        return html_template
    
    def _get_color_scheme(self) -> dict:
        """根据配置获取配色方案"""
        schemes = {
            'premium': {
                'primary': '#6366f1',
                'secondary': '#8b5cf6',
                'accent': '#ec4899'
            },
            'minimal': {
                'primary': '#0ea5e9',
                'secondary': '#06b6d4',
                'accent': '#14b8a6'
            },
            'warm': {
                'primary': '#f59e0b',
                'secondary': '#f97316',
                'accent': '#ef4444'
            }
        }
        
        # 根据 variance 选择配色
        if self.variance >= 7:
            return schemes['premium']
        elif self.variance >= 4:
            return schemes['minimal']
        else:
            return schemes['warm']
    
    def save_html(self, html_content: str, filepath: str):
        """保存 HTML 文件"""
        os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else '.', exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"✅ HTML 报告已保存: {filepath}")


# ============================================================
# 使用示例
# ============================================================

if __name__ == "__main__":
    # 创建增强器实例
    enhancer = TasteSkillReportEnhancer(variance=7, motion=5, density=4)
    
    # 示例 Markdown 内容
    sample_markdown = """
📊 投资组合优化与回测报告
生成时间: 2026-06-07 10:30:00

📋 持仓清单:
  511360 - 短融ETF海富通 (money, low)
  518880 - 黄金ETF华安 (commodity, medium)

📈 策略表现汇总:

等权重策略:
  总收益率: 3.07%
  年化收益: 12.28%
  夏普比率: 0.11
  最大回撤: -16.82%

🏆 最佳策略: 等权重
   夏普比率: 0.11
   收益率: 3.07%
"""
    
    # 生成精美 HTML 报告
    html_report = enhancer.enhance_markdown_to_html(
        sample_markdown,
        title="投资组合优化报告",
        save_path="reports/sample_report.html"
    )
    
    print("✅ 报告生成完成！")
