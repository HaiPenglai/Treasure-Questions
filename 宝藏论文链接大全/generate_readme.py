"""
宝藏论文链接大全 - README 生成脚本

功能：
1. 读取 papers.json，按 video_id 倒序生成 README.md
2. 支持命令行直接打印列表到终端
3. 格式与主 README 保持一致：三级标题 + 观看视频 + 阅读论文

用法：
    python generate_readme.py          # 生成 README.md
    python generate_readme.py --print  # 终端打印列表
"""
import json
import os
import sys

JSON_FILE = "papers.json"
README_FILE = "README.md"


def load_papers():
    """读取 papers.json，确保按 video_id 倒序排列"""
    with open(JSON_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    # 强制按 video_id 降序排列（最新的在前面）
    data.sort(key=lambda x: x.get("video_id", 0), reverse=True)
    return data


def format_readme(papers):
    """生成 README.md 的 Markdown 内容"""
    lines = []
    lines.append("# 宝藏论文链接大全")
    lines.append("")
    lines.append("")
    lines.append("---")
    lines.append("")

    for item in papers:
        video_title = item.get("video_title", "")
        bvid = item.get("bvid", "")
        papers_list = item.get("papers", [])
        video_url = f"https://www.bilibili.com/video/{bvid}" if bvid else ""

        lines.append(f"### {video_title}")
        if bvid:
            lines.append(f"- 观看视频：[{bvid}]({video_url})")
        else:
            lines.append("- 观看视频：（暂未收录）")
        lines.append("")

        if not papers_list:
            lines.append("- 阅读论文：*暂无论文链接*")
        else:
            for p in papers_list:
                title = p.get("paper_title", "")
                link = p.get("paper_link", "")
                if link:
                    lines.append(f"- 阅读论文：[{title}]({link})")
                else:
                    lines.append(f"- 阅读论文：{title}")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def print_to_terminal(papers):
    """在终端以表格形式打印"""
    # 计算列宽
    max_video = max(len(item["video_title"]) for item in papers)
    max_paper = max(
        len(p.get("paper_title", ""))
        for item in papers
        for p in item.get("papers", [])
    )
    # 留一些边距
    col1_width = min(max_video + 2, 60)
    col2_width = min(max_paper + 2, 70)

    header = f"{'视频标题':<{col1_width}} | {'论文标题':<{col2_width}} | 论文链接"
    print(header)
    print("-" * len(header))

    for item in papers:
        video_title = item.get("video_title", "")
        papers_list = item.get("papers", [])
        if not papers_list:
            print(f"{video_title:<{col1_width}} | {'(无)':<{col2_width}} | ")
        else:
            for i, p in enumerate(papers_list):
                title = p.get("paper_title", "")
                link = p.get("paper_link", "")
                v_display = video_title if i == 0 else ""
                print(f"{v_display:<{col1_width}} | {title:<{col2_width}} | {link}")
        print("-" * len(header))


def main():
    papers = load_papers()

    if len(sys.argv) > 1 and sys.argv[1] in ("--print", "-p"):
        print_to_terminal(papers)
    else:
        content = format_readme(papers)
        with open(README_FILE, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[OK] {README_FILE} 已生成，共 {len(papers)} 个视频。")


if __name__ == "__main__":
    main()
