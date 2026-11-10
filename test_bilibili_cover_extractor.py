"""封面分类与 README 时间排序的离线检查，不访问 B站。"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch
from PIL import Image

import bilibili_cover_extractor as covers


class CoverTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.base = Path(__file__).resolve().parent / ".render_tmp" / "cover-tests"
        self.base.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=self.base)
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()
        self.base.rmdir()

    async def test_all_question_suffixes_download_into_the_same_cover_directory(self):
        def ffmpeg(command, **kwargs):
            Image.new("RGB", (1728, 1080)).save(command[-1])
            return type("Result", (), {"returncode": 0})()

        with patch.object(covers, "OUTPUT_DIR", str(self.root / "assets")), \
                patch.object(covers, "get_video_stream_url", AsyncMock(return_value="https://example.invalid/video")), \
                patch.object(covers.subprocess, "run", side_effect=ffmpeg):
            for index, suffix in enumerate(covers.QUESTION_SUFFIXES):
                title = f"[1]. 测试{suffix}"
                bv = f"BVtest{index}"
                self.assertEqual(covers.get_category(title), "questions")
                self.assertTrue(await covers.extract_first_frame(bv, title))
                self.assertTrue((self.root / f"assets/questions/{bv}.jpg").is_file())
                self.assertEqual(covers.simplify_title(title), "[1]. 测试")

    async def test_best_stream_is_selected_by_resolution_even_if_api_order_changes(self):
        info = {"dash": {"video": [
            {"baseUrl": "480p", "width": 768, "height": 480, "id": 32},
            {"baseUrl": "1080p", "width": 1728, "height": 1080, "id": 80},
            {"baseUrl": "720p", "width": 1152, "height": 720, "id": 64},
        ]}}
        with patch.object(covers.video.Video, "get_download_url", AsyncMock(return_value=info)):
            self.assertEqual(await covers.get_video_stream_url("BV1DdJi6uEqT"), "1080p")
            info["dash"]["video"] = info["dash"]["video"][:1]
            self.assertEqual(await covers.get_video_stream_url("BV1DdJi6uEqT"), "")

    async def test_low_resolution_download_cannot_replace_existing_image(self):
        target = self.root / "questions" / "BVtest.jpg"
        target.parent.mkdir()
        Image.new("RGB", (768, 480), "red").save(target)
        original = target.read_bytes()

        def ffmpeg(command, **kwargs):
            Image.new("RGB", (768, 480), "blue").save(command[-1])
            return type("Result", (), {"returncode": 0})()

        with patch.object(covers, "OUTPUT_DIR", str(self.root)), \
                patch.object(covers, "get_video_stream_url", AsyncMock(return_value="stream")), \
                patch.object(covers, "download_stream_prefix", return_value=b""), \
                patch.object(covers.subprocess, "run", side_effect=ffmpeg):
            self.assertFalse(await covers.extract_first_frame("BVtest", "271. 测试【每天一个宝藏问题】"))
        self.assertEqual(target.read_bytes(), original)
        self.assertFalse(Path(str(target) + ".tmp.jpg").exists())

    async def test_batch_repairs_low_resolution_and_skips_valid_cover(self):
        folder = self.root / "questions"
        folder.mkdir()
        Image.new("RGB", (768, 480)).save(folder / "BVlow.jpg")
        Image.new("RGB", (1728, 1080)).save(folder / "BVgood.jpg")
        items = [{"bvid": bv, "title": "271. 测试【每天一个宝藏问题】"}
                 for bv in ("BVlow", "BVgood")]

        def ffmpeg(command, **kwargs):
            Image.new("RGB", (1728, 1080)).save(command[-1])
            return type("Result", (), {"returncode": 0})()

        with patch.object(covers, "OUTPUT_DIR", str(self.root)), \
                patch.object(covers, "refresh_video_info", AsyncMock(return_value=None)), \
                patch.object(covers, "get_video_stream_url", AsyncMock(return_value="stream")), \
                patch.object(covers.subprocess, "run", side_effect=ffmpeg), \
                patch.object(covers.asyncio, "sleep", AsyncMock()):
            self.assertEqual(await covers.batch_extract(items), (1, 0))
        self.assertTrue(covers.cover_is_high_resolution(str(folder / "BVlow.jpg"), "BVlow"))

    def test_readme_orders_mixed_series_by_publication_and_retains_paper_number_order(self):
        readme = self.root / "README.md"
        readme.write_text("# 宝藏问题\n\n保留我的说明\n\n## 每天一个宝藏问题\n\n旧列表\n\n## 每天一个宝藏论文\n\n旧列表\n", encoding="utf-8")
        items = [
            {"bvid": "BVold", "title": "280. 问题【每天一个宝藏问题】", "created": 100},
            {"bvid": "BVanime", "title": "[1]. 动画【宝藏问题动画版】", "created": 300},
            {"bvid": "BVmerged", "title": "<2>. 合集【宝藏问题一口气看完】", "created": 200},
            {"bvid": "BVnodate", "title": "999. 缺日期【每天一个宝藏问题】"},
            {"bvid": "BVpaper1", "title": "[1]. 论文【每天一个宝藏论文】", "created": 400},
            {"bvid": "BVpaper2", "title": "[2]. 论文【每天一个宝藏论文】", "created": 100},
        ]
        with patch.object(covers, "README_FILE", str(readme)):
            covers.update_readme(items)
            first = readme.read_text(encoding="utf-8")
            covers.update_readme(list(reversed(items)))
            self.assertEqual(readme.read_text(encoding="utf-8"), first)
        self.assertIn("保留我的说明", first)
        positions = [first.index("### " + items[i]["title"]) for i in (1, 2, 0, 3)]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("./assets/questions/BVanime.jpg", first)
        self.assertIn("./assets/questions/BVmerged.jpg", first)
        self.assertLess(first.index("### " + items[5]["title"]), first.index("### " + items[4]["title"]))
        self.assertEqual(covers.extract_number("<2>. 合集"), 2)
        self.assertEqual(covers.publication_time({"pubdate": "123"}), 123)


if __name__ == "__main__":
    unittest.main()
