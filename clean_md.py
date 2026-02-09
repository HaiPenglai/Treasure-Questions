import os
import re
import sys
import win32com.client

# --- 配置区 ---
PPT_PREFIX = "宝藏问题"  # PPT文件的前缀，如 宝藏问题1.pptx, 宝藏问题2.pptx
ASSETS_DIR = "assets"
README_FILE = "README.md"
EXPORT_WIDTH = 1920 
EXPORT_HEIGHT = 1080

def get_referenced_images():
    """从 README 中提取所有引用的图片标签 (格式如: 1_123)"""
    if not os.path.exists(README_FILE):
        return set()
    with open(README_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    # 匹配 assets/1_123.png 其中的 1_123
    return set(re.findall(r'assets[/\\](\d+_\d+)\.png', content))

def export_images(image_tags):
    """精准导出指定的图片标签列表"""
    if not image_tags:
        print("没有需要导出的图片。")
        return

    # 1. 按 PPT 文件对任务进行分组
    tasks = {} # { ppt_idx: [ (page_num, img_tag), ... ] }
    for tag in sorted(image_tags):
        try:
            ppt_idx, page_num = tag.split('_')
            tasks.setdefault(ppt_idx, []).append((int(page_num), tag))
        except ValueError:
            print(f"警告: 标签 {tag} 格式不正确，应为 'PPT编号_页码'")
            continue

    # 2. 启动 PPT 引擎
    try:
        try: app = win32com.client.Dispatch("PowerPoint.Application")
        except: app = win32com.client.Dispatch("KWPP.Application")
    except Exception as e:
        print(f"无法启动 PPT 引擎: {e}")
        return

    abs_assets = os.path.abspath(ASSETS_DIR)
    if not os.path.exists(abs_assets): os.makedirs(abs_assets)

    for ppt_idx, slide_tasks in tasks.items():
        ppt_name = f"{PPT_PREFIX}{ppt_idx}.pptx"
        if not os.path.exists(ppt_name):
            print(f"警告: 找不到文件 {ppt_name}，跳过该组图片。")
            continue

        print(f"正在打开 {ppt_name} 导出 {len(slide_tasks)} 张图片...")
        try:
            pres = app.Presentations.Open(os.path.abspath(ppt_name), WithWindow=False)
            for page_num, img_tag in slide_tasks:
                if page_num > pres.Slides.Count or page_num < 1:
                    print(f"  错误: {ppt_name} 只有 {pres.Slides.Count} 页，无法导出第 {page_num} 页。")
                    continue
                
                export_path = os.path.join(abs_assets, f"{img_tag}.png")
                pres.Slides(page_num).Export(export_path, "PNG", EXPORT_WIDTH, EXPORT_HEIGHT)
                print(f"  成功导出: {img_tag}.png")
            pres.Close()
        except Exception as e:
            print(f"处理 {ppt_name} 时出错: {e}")

    app.Quit()

def generate_github_anchor(text):
    anchor = text.lower().strip()
    anchor = re.sub(r'[^\w\s\-]', '', anchor)
    anchor = anchor.replace(' ', '-')
    return anchor

def update_toc_and_clean():
    """更新 TOC 并清理 README 没引用的多余图片"""
    if not os.path.exists(README_FILE): return
    with open(README_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. 更新 TOC (保持原逻辑)
    lines = content.splitlines()
    toc_list = []
    for line in lines:
        match = re.match(r'^(#{2,6})\s+(.*)', line)
        if match:
            level = len(match.group(1))
            title = match.group(2).strip()
            anchor = generate_github_anchor(title)
            indent = "  " * (level - 2)
            toc_list.append(f"{indent}- [{title}](#{anchor})")
    
    if "<TOC>" in content:
        toc_str = "\n" + "\n".join(toc_list) + "\n\n"
        # 用<TOC>标记，而不是[TOC]，否则typora中会生成2个目录。
        content = re.sub(r'(?:\[TOC\]|<TOC>).*?(?=\n#|---|$)', f'<TOC>\n{toc_str}', content, flags=re.DOTALL)

    # 2. 清理冗余图片 (只清理符合 \d+_\d+.png 格式但未被引用的)
    referenced = set(f"{tag}.png" for tag in re.findall(r'assets[/\\](\d+_\d+)\.png', content))
    if os.path.exists(ASSETS_DIR):
        for f in os.listdir(ASSETS_DIR):
            # 只有符合新命名规则的才参与自动清理，防止误删主公手动放入的代码图
            if re.match(r'\d+_\d+\.png', f) and f not in referenced:
                os.remove(os.path.join(ASSETS_DIR, f))
                print(f"清理冗余图片: {f}")

    with open(README_FILE, 'w', encoding='utf-8') as f:
        f.write(content)
    print("README 更新与清理完成。")

if __name__ == "__main__":
    print("=== PPT精准页码转图片工具 ===")
    
    if len(sys.argv) > 1:
        # 模式 A: 强制导出指定标签 python clean_md.py 1_123
        target_tags = [sys.argv[1]]
        print(f"执行强制单图导出模式: {target_tags[0]}.png")
    else:
        # 模式 B: 自动检查模式
        print("执行自动检查模式...")
        referenced = get_referenced_images()
        # 找出已引用但本地不存在的图片
        target_tags = [tag for tag in referenced if not os.path.exists(os.path.join(ASSETS_DIR, f"{tag}.png"))]
        
        if not target_tags:
            print("README 中引用的图片均已存在，无需重复导出。")
            print("提示: 若需更新某页，请删除 assets 下对应图片或运行 'python clean_md.py [编号_页码]'")
        else:
            print(f"发现新引用标签: {target_tags}")

    # 执行导出
    if target_tags:
        export_images(target_tags)
    
    # 执行收尾
    update_toc_and_clean()
    print("=== 任务完成 ===")