"""
B站视频第一帧封面提取流水线 v4 - 使用BVID作为文件名（避免GitHub中文路径问题）
- 文件名使用BVID（如 BV1qAA5ztELy.jpg）
- 按视频分类存放（questions/papers/experiments/terms/others）
- 自动更新 README.md 生成视频列表（带序号排序和简化标题）
- 带反爬虫延迟
- 自动发现新发布的视频（基于时间戳增量更新）

使用方法:
    python bilibili_cover_extractor.py
    
无需任何参数，每周运行一次即可自动添加新视频。
"""
import os
import re
import json
import subprocess
import asyncio
import time
import urllib.request
from bilibili_api import user, video

MID = 2071007724
OUTPUT_DIR = "assets"
BV_LIST_FILE = "bv_list.json"
README_FILE = "README.md"

# 分类配置
CATEGORIES = {
    "questions": "宝藏问题",
    "terms": "宝藏名词", 
    "papers": "宝藏论文",
    "experiments": "宝藏实验"
}

# README 中的分类标题映射
README_SECTIONS = {
    "questions": "## 每天一个宝藏问题",
    "terms": "## 每天一个宝藏名词",
    "papers": "## 每周一个宝藏论文",
    "experiments": "## 每周一个宝藏实验",
    "others": "## 其他"
}


def get_category(title: str) -> str:
    """根据标题判断分类目录"""
    for cat_dir, keyword in CATEGORIES.items():
        if keyword in title:
            return cat_dir
    return "others"


def extract_number(title: str) -> int:
    """从标题中提取序号，用于排序（更鲁棒的版本）"""
    # 先尝试匹配各种格式：
    # 1. 数字. 或 数字：或 数字、 或 数字 后跟空格
    # 2. [数字] 或 【数字】 或 ［数字］
    patterns = [
        r'^(\d+)[\.:\s、]\s*',           # 67.  67:  67  67、
        r'^\[(\d+)\]',                    # [67]
        r'^【(\d+)】',                    # 【67】
        r'^［(\d+)］',                    # ［67］
        r'^(\d+)',                        # 67（兜底，只要开头是数字）
    ]
    
    for pattern in patterns:
        match = re.match(pattern, title)
        if match:
            return int(match.group(1))
    
    return 0


def simplify_title(title: str) -> str:
    """
    简化标题：去掉分类标签后缀
    例如：
    "67. 为何圆形山谷会让OBD剪枝退化为基于大小剪枝？【每天一个宝藏问题】"
    -> "67. 为何圆形山谷会让OBD剪枝退化为基于大小剪枝？"
    """
    # 去掉所有分类标签
    for keyword in CATEGORIES.values():
        title = re.sub(rf'【{keyword}】', '', title)
        title = re.sub(rf'\[每天一个[^\]]+\]', '', title)
        title = re.sub(rf'\[每周一个[^\]]+\]', '', title)
    
    # 清理首尾空格
    return title.strip()


def ensure_dir(category: str = ""):
    """创建分类目录"""
    if category:
        path = os.path.join(OUTPUT_DIR, category)
    else:
        path = OUTPUT_DIR
    os.makedirs(path, exist_ok=True)


async def refresh_video_info(bv: str) -> dict:
    """获取单个视频的最新信息（用于刷新标题）"""
    try:
        v = video.Video(bvid=bv)
        info = await v.get_info()
        return {
            "bvid": info.get("bvid", bv),
            "title": info.get("title", ""),
            "created": info.get("pub_date", 0),
            "pic": info.get("pic", "")
        }
    except Exception as e:
        print(f"  [{bv}] 获取视频信息失败: {str(e)[:80]}")
        return None


async def fetch_new_bvs(last_update_time: float) -> list:
    """
    增量获取新视频（created > last_update_time）
    使用优化策略：只检查最新几页，遇到旧视频立即停止
    """
    u = user.User(MID)
    new_bvs = []
    pn = 1
    
    print(f"[Fetch] 检查新视频（发布时间 > {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(last_update_time))}）...")
    
    while True:
        print(f"[Fetch] 正在获取第 {pn} 页...")
        try:
            videos = await u.get_videos(pn=pn, ps=30)
        except Exception as e:
            print(f"[Fetch] 第 {pn} 页失败（可能触发风控），已获取 {len(new_bvs)} 个新视频。错误: {str(e)[:100]}")
            break
        
        vlist = videos.get("list", {}).get("vlist", [])
        if not vlist:
            print("[Fetch] 没有更多视频了。")
            break
        
        # 检查本页视频
        found_old = False
        for v in vlist:
            created = v["created"]
            if created > last_update_time:
                # 这是新视频
                new_bvs.append({
                    "bvid": v["bvid"],
                    "title": v["title"],
                    "created": v["created"],
                    "pic": v["pic"]
                })
            else:
                # 遇到旧视频，停止检查
                found_old = True
                break
        
        print(f"[Fetch] 第 {pn} 页检查完成，本页新视频 {len(new_bvs)} 个，累计 {len(new_bvs)} 个")
        
        if found_old:
            print("[Fetch] 已遇到旧视频，停止检查更早的视频。")
            break
        
        if len(vlist) < 30:
            print("[Fetch] 已到达最后一页。")
            break
        
        pn += 1
        await asyncio.sleep(6)  # 翻页前等待，降低风控概率
    
    return new_bvs


async def fetch_all_bvs():
    """首次运行：获取UP主全部视频列表"""
    u = user.User(MID)
    all_bvs = []
    pn = 1
    
    print("[Fetch] 首次运行，获取全部视频列表...")
    
    while True:
        print(f"[Fetch] 正在获取第 {pn} 页...")
        try:
            videos = await u.get_videos(pn=pn, ps=30)
        except Exception as e:
            print(f"[Fetch] 第 {pn} 页失败（可能触发风控），已获取 {len(all_bvs)} 个。错误: {str(e)[:100]}")
            break
        
        vlist = videos.get("list", {}).get("vlist", [])
        if not vlist:
            print("[Fetch] 没有更多视频了。")
            break
        
        for v in vlist:
            all_bvs.append({
                "bvid": v["bvid"],
                "title": v["title"],
                "created": v["created"],
                "pic": v["pic"]
            })
        
        print(f"[Fetch] 第 {pn} 页成功，本页 {len(vlist)} 个，累计 {len(all_bvs)} 个")
        
        if len(vlist) < 30:
            break
        
        pn += 1
        await asyncio.sleep(6)  # 翻页前等待，降低风控概率
    
    with open(BV_LIST_FILE, "w", encoding="utf-8") as f:
        json.dump(all_bvs, f, ensure_ascii=False, indent=2)
    
    print(f"[Fetch] BV列表已保存到 {BV_LIST_FILE}，共 {len(all_bvs)} 个")
    return all_bvs


def download_pic(bv: str, pic_url: str, output_path: str) -> bool:
    """直接下载 B 站 API 返回的封面图（fallback 方案）"""
    try:
        req = urllib.request.Request(
            pic_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
                "Referer": "https://www.bilibili.com",
            }
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
            if len(data) > 2000:
                with open(output_path, "wb") as f:
                    f.write(data)
                size_kb = len(data) // 1024
                print(f"  [{bv}] OK(pic) {size_kb}KB -> {output_path}")
                return True
    except Exception as e:
        print(f"  [{bv}] pic下载失败: {str(e)[:80]}")
    return False


def extract_first_frame(bv: str, title: str, pic: str = None) -> bool:
    """提取单个BV视频的第一帧，使用BVID作为文件名，自动分类。
    yt-dlp 被风控时自动 fallback 到 API 返回的 pic 封面图。"""
    # 确定分类和输出目录
    category = get_category(title)
    ensure_dir(category)
    output_dir = os.path.join(OUTPUT_DIR, category)
    
    # 文件名就是 bvid.jpg
    output_path = os.path.join(output_dir, f"{bv}.jpg")
    
    if os.path.exists(output_path):
        print(f"  [{bv}] 已存在，跳过")
        return True
    
    url = f"https://www.bilibili.com/video/{bv}"
    
    # 先尝试 yt-dlp + ffmpeg 提取第一帧（原有逻辑）
    try:
        get_url_cmd = f'yt-dlp -g -f bestvideo "{url}"'
        stream_url = subprocess.check_output(
            get_url_cmd, shell=True, text=True, timeout=40
        ).strip().split("\n")[0]
        if stream_url:
            headers = (
                "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36\r\n"
                "Referer: https://www.bilibili.com\r\n"
            )
            ffmpeg_cmd = [
                "ffmpeg", "-y",
                "-headers", headers,
                "-i", stream_url,
                "-ss", "00:00:00",
                "-vframes", "1",
                "-q:v", "1",
                "-pix_fmt", "yuvj420p",
                output_path
            ]
            result = subprocess.run(
                ffmpeg_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=40
            )
            if result.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 2000:
                size_kb = os.path.getsize(output_path) // 1024
                print(f"  [{bv}] OK(ffmpeg) {size_kb}KB -> {category}/{bv}.jpg")
                return True
    except subprocess.TimeoutExpired:
        print(f"  [{bv}] ffmpeg 超时，尝试 fallback...")
    except Exception:
        pass  # yt-dlp 失败，静默继续 fallback
    
    # Fallback：用 B 站 API 返回的 pic 直接下载封面
    if pic:
        print(f"  [{bv}] yt-dlp 被风控，fallback 到 pic 封面下载...")
        if download_pic(bv, pic, output_path):
            return True
    
    print(f"  [{bv}] X 未生成有效图片")
    return False


async def batch_extract(bv_list):
    """批量提取封面，带全局延迟降低风控。封面缺失时自动刷新标题，自动分类。"""
    total = len(bv_list)
    success = 0
    skipped = 0
    failed = 0
    updated = 0
    
    # 按分类统计
    stats = {cat: 0 for cat in list(CATEGORIES.keys()) + ["others"]}
    
    print(f"[Extract] 开始检查 {total} 个视频的封面...")
    
    for i, item in enumerate(bv_list, 1):
        bv = item["bvid"]
        title = item["title"]
        
        # 确定分类
        category = get_category(title)
        stats[category] += 1
        
        # 确定输出路径（分类目录/bvid.jpg）
        ensure_dir(category)
        output_path = os.path.join(OUTPUT_DIR, category, f"{bv}.jpg")
        
        # 检查是否已存在
        if os.path.exists(output_path):
            skipped += 1
            continue  # 静默跳过已存在的，减少输出噪音
        
        # 封面缺失！先刷新标题（从B站获取最新标题）
        print(f"[{i}/{total}] [{category}] 封面缺失: {bv}")
        fresh_info = await refresh_video_info(bv)
        if fresh_info and fresh_info["title"]:
            old_title = item["title"]
            new_title = fresh_info["title"]
            if old_title != new_title:
                print(f"  标题已更新: {old_title[:40]}... -> {new_title[:40]}...")
                item["title"] = new_title
                item["pic"] = fresh_info["pic"]
                updated += 1
                # 重新计算分类（可能标题变了分类也变了）
                category = get_category(new_title)
            title = new_title
        
        # 使用（可能更新后的）标题下载
        print(f"[{i}/{total}] 提取封面: {title[:50]}...")
        pic_url = item.get("pic", "")
        if extract_first_frame(bv, title, pic_url):
            success += 1
        else:
            failed += 1
        
        # 每个视频处理完都休息 2.5 秒，降低对 B 站 CDN 的压力
        time.sleep(2.5)
    
    print(f"[Extract] 完成！成功 {success} 个，跳过 {skipped} 个，失败 {failed} 个")
    if updated > 0:
        print(f"[Extract] 更新了 {updated} 个视频的标题")
    
    # 打印分类统计
    print("\n[Extract] 分类统计:")
    for cat, count in stats.items():
        if count > 0:
            print(f"  {cat:12}: {count} 个")
    
    return success, updated


def update_readme(bv_list):
    """更新 README.md，生成视频列表（带序号排序，图片无说明文字，减少token）"""
    print("\n[README] 开始更新 README.md...")
    
    # 按分类分组
    categorized = {cat: [] for cat in list(CATEGORIES.keys()) + ["others"]}
    for item in bv_list:
        category = get_category(item["title"])
        categorized[category].append(item)
    
    # 读取现有 README
    if os.path.exists(README_FILE):
        with open(README_FILE, "r", encoding="utf-8") as f:
            content = f.read()
    else:
        # 创建默认 README 结构
        content = """# 宝藏问题

- **作者**：b站**海安雨**。

## 每天一个宝藏问题

## 每天一个宝藏名词

## 每周一个宝藏论文

## 每周一个宝藏实验

## 其他

"""
    
    # 为每个分类生成内容并替换
    for category, section_title in README_SECTIONS.items():
        # 按序号排序（从大到小，最新的在前面）
        items = categorized[category]
        items.sort(key=lambda x: extract_number(x["title"]), reverse=True)
        
        # 生成该分类的内容
        lines = []
        for item in items:
            bv = item["bvid"]
            full_title = item["title"]
            img_path = f"./assets/{category}/{bv}.jpg"
            
            # 格式（减少token）：
            # 完整标题（包含序号和分类标签）
            # ![](路径)  <- 图片无说明文字
            # ---
            lines.append(f"{full_title}")
            lines.append(f"![]({img_path})")
            lines.append("---")
            lines.append("")  # 空行分隔
        
        section_content = "\n".join(lines) if lines else "*暂无视频*\n"
        
        # 使用正则替换该部分的内容
        # 匹配模式: ## 标题\n\n(内容)\n(?=## 或结尾)
        pattern = rf"({re.escape(section_title)}\n\n)(.*?)(?=\n## |\Z)"
        
        def replace_section(match):
            return f"{match.group(1)}{section_content}"
        
        new_content, count = re.subn(pattern, replace_section, content, flags=re.DOTALL)
        if count > 0:
            content = new_content
            print(f"  [{category}] 已更新 {len(items)} 个视频（按序号排序）")
        else:
            print(f"  [{category}] 未找到对应章节，跳过")
    
    # 保存更新后的 README
    with open(README_FILE, "w", encoding="utf-8") as f:
        f.write(content)
    
    print(f"[README] 已更新 {README_FILE}")


async def main():
    ensure_dir()
    
    # 步骤1：获取BV列表（基于时间的增量更新）
    if os.path.exists(BV_LIST_FILE):
        # 获取上次更新时间（文件修改时间）
        last_update_time = os.path.getmtime(BV_LIST_FILE)
        print(f"[Main] 上次更新时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(last_update_time))}")
        
        # 加载现有列表
        with open(BV_LIST_FILE, "r", encoding="utf-8") as f:
            bv_list = json.load(f)
        print(f"[Main] 现有视频: {len(bv_list)} 个")
        
        # 获取新视频（发布时间 > 上次更新时间）
        new_bvs = await fetch_new_bvs(last_update_time)
        
        if new_bvs:
            print(f"[Main] 发现 {len(new_bvs)} 个新视频")
            
            # 去重并合并（新视频插入到列表开头，保持时间倒序）
            existing_bvids = {v["bvid"] for v in bv_list}
            added_count = 0
            for v in reversed(new_bvs):  # 反转一下，让最早的新视频先插入，最终列表是按时间倒序
                if v["bvid"] not in existing_bvids:
                    bv_list.insert(0, v)
                    added_count += 1
            
            # 保存更新后的列表（同时更新时间戳）
            with open(BV_LIST_FILE, "w", encoding="utf-8") as f:
                json.dump(bv_list, f, ensure_ascii=False, indent=2)
            print(f"[Main] 已更新 {BV_LIST_FILE}，新增 {added_count} 个，共 {len(bv_list)} 个视频")
        else:
            print("[Main] 没有发现新视频")
    else:
        # 首次运行，获取全部
        print("[Main] 首次运行，获取全部视频...")
        bv_list = await fetch_all_bvs()
    
    # 步骤2：批量提取封面（只下载缺失的）
    if bv_list:
        success, updated = await batch_extract(bv_list)
        
        # 如果有标题被更新，保存json
        if updated > 0:
            with open(BV_LIST_FILE, "w", encoding="utf-8") as f:
                json.dump(bv_list, f, ensure_ascii=False, indent=2)
            print(f"[Main] 已更新 {BV_LIST_FILE} 中的 {updated} 个视频标题")
    else:
        print("[Main] 没有BV号可处理")
    
    # 步骤3：更新 README.md（每次都会刷新，无论是否有新下载）
    if bv_list:
        update_readme(bv_list)


if __name__ == "__main__":
    asyncio.run(main())
