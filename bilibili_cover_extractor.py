"""
B站视频第一帧封面提取流水线 v3 - 基于时间的自动发现
- 使用视频标题作为文件名
- 最高质量 JPG 提取，不做无谓放大
- 带反爬虫延迟
- 自动发现新发布的视频（基于时间戳增量更新）

使用方法：
    python bilibili_cover_extractor.py
    
无需任何参数，每周运行一次即可自动添加新视频。
"""
import os
import re
import json
import subprocess
import asyncio
import time
from bilibili_api import user, video

MID = 2071007724
OUTPUT_DIR = "assets"
BV_LIST_FILE = "bv_list.json"

# 开关
USE_TITLE_AS_FILENAME = True   # True=用标题命名, False=用BV号命名
MAX_FILENAME_LEN = 150         # 文件名最大长度（不含扩展名）

# 分类配置
CATEGORIES = {
    "questions": "宝藏问题",
    "terms": "宝藏名词",
    "papers": "宝藏论文",
    "experiments": "宝藏实验"
}


def get_category(title: str) -> str:
    """根据标题判断分类目录"""
    for cat_dir, keyword in CATEGORIES.items():
        if keyword in title:
            return cat_dir
    return "others"


def sanitize_filename(name: str, remove_category_tag: bool = True) -> str:
    """
    清理文件名：
    1. 【10】 -> [10] (中文黑括号转英文中括号，保留序号)
    2. 移除分类标签如 [每周一个宝藏论文]（因为已用目录分类）
    3. 中文冒号 ： -> _
    4. 最终格式: [10] 标题内容.jpg 或 10. 标题内容.jpg
    """
    # 步骤1: 将所有中文黑括号 【】 转为英文中括号 []
    name = name.replace('【', '[')
    name = name.replace('】', ']')
    
    # 步骤2: 提取序号（匹配 [数字] 或 数字. 开头）
    # 匹配 [10] 或 10. 或 10 开头
    prefix_match = re.match(r'^(\[\d+\]|\d+\.)\s*', name)
    prefix = ""
    if prefix_match:
        prefix = prefix_match.group(1).strip()
        name = name[prefix_match.end():].strip()
    
    # 步骤3: 移除分类标签 [宝藏问题] [宝藏名词] [宝藏论文] [宝藏实验]
    if remove_category_tag:
        for keyword in CATEGORIES.values():
            name = re.sub(rf'\[{keyword}\]', '', name)
        # 同时移除每周/每天的变体
        name = re.sub(r'\[每周一个[^\]]+\]', '', name)
        name = re.sub(r'\[每天一个[^\]]+\]', '', name)
    
    # 步骤4: 中文冒号 -> 下划线
    name = name.replace('：', '_')
    name = name.replace(':', '_')
    
    # 步骤5: 移除其他非法字符
    name = re.sub(r'[\\/*?"<>|]', '_', name)
    
    # 步骤6: 清理连续下划线和空格
    name = re.sub(r'_+', '_', name)
    name = re.sub(r' +', ' ', name)
    name = name.strip(' _')
    
    # 步骤7: 组合回去
    # 如果有序号，保持 [10] 格式或转为 10. 格式
    if prefix:
        # 将 [10] 转为 10. 格式更统一
        prefix = re.sub(r'\[(\d+)\]', r'\1.', prefix)
        # 移除末尾多余的点
        prefix = re.sub(r'\.$', '', prefix)
        return f"{prefix}. {name}" if name else f"{prefix}.jpg"
    
    return name or "untitled"


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


def extract_first_frame(bv: str, title: str, category: str = "") -> bool:
    """提取单个BV视频的第一帧，最高质量，不做放大，自动分类"""
    # 确定输出目录
    if category:
        ensure_dir(category)
        output_dir = os.path.join(OUTPUT_DIR, category)
    else:
        ensure_dir()
        output_dir = OUTPUT_DIR
    
    if USE_TITLE_AS_FILENAME:
        base_name = sanitize_filename(title, remove_category_tag=True)
        output_path = os.path.join(output_dir, f"{base_name}.jpg")
    else:
        output_path = os.path.join(output_dir, f"{bv}_first_frame.jpg")
    
    if os.path.exists(output_path):
        print(f"  [{bv}] 已存在，跳过")
        return True
    
    url = f"https://www.bilibili.com/video/{bv}"
    
    try:
        # 1. yt-dlp 获取最佳视频流
        get_url_cmd = f'yt-dlp -g -f bestvideo "{url}"'
        stream_url = subprocess.check_output(
            get_url_cmd, shell=True, text=True, timeout=40
        ).strip().split("\n")[0]
        if not stream_url:
            print(f"  [{bv}] X 无法获取视频流")
            return False
        
        # 2. ffmpeg 提取第一帧，最高质量 JPG
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
            "-q:v", "1",          # JPG 最高质量
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
            print(f"  [{bv}] OK {size_kb}KB -> {os.path.basename(output_path)}")
            return True
        else:
            print(f"  [{bv}] X 未生成有效图片")
            return False
    
    except subprocess.TimeoutExpired:
        print(f"  [{bv}] X 超时")
        return False
    except Exception as e:
        print(f"  [{bv}] X 错误: {str(e)[:80]}")
        return False


async def batch_extract(bv_list):
    """批量提取封面，带全局延迟降低风控。封面缺失时自动刷新标题，自动分类。"""
    total = len(bv_list)
    success = 0
    skipped = 0
    failed = 0
    updated = 0  # 记录更新标题的数量
    
    # 按分类统计
    stats = {cat: 0 for cat in list(CATEGORIES.keys()) + ["others"]}
    
    print(f"[Extract] 开始检查 {total} 个视频的封面...")
    
    for i, item in enumerate(bv_list, 1):
        bv = item["bvid"]
        title = item["title"]
        
        # 确定分类
        category = get_category(title)
        stats[category] += 1
        
        # 确定输出路径（分类目录）
        ensure_dir(category)
        if USE_TITLE_AS_FILENAME:
            base_name = sanitize_filename(title, remove_category_tag=True)
            output_path = os.path.join(OUTPUT_DIR, category, f"{base_name}.jpg")
        else:
            output_path = os.path.join(OUTPUT_DIR, category, f"{bv}_first_frame.jpg")
        
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
            title = new_title
        
        # 使用（可能更新后的）标题下载，传递分类
        print(f"[{i}/{total}] 提取封面: {title[:50]}...")
        if extract_first_frame(bv, title, category):
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
    
    # 步骤2：批量提取封面
    if bv_list:
        success, updated = await batch_extract(bv_list)
        
        # 如果有标题被更新，保存json
        if updated > 0:
            with open(BV_LIST_FILE, "w", encoding="utf-8") as f:
                json.dump(bv_list, f, ensure_ascii=False, indent=2)
            print(f"[Main] 已更新 {BV_LIST_FILE} 中的 {updated} 个视频标题")
    else:
        print("[Main] 没有BV号可处理")


if __name__ == "__main__":
    asyncio.run(main())
