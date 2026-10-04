"""T1: extract.py 测试 — 用合成 PDF 验证提取逻辑。"""
import pymupdf
import pytest

from wordhelper.extract import extract_pages


@pytest.fixture
def tiny_pdf(tmp_path):
    """生成一个 2 页的合成 PDF，含中英文文本行。"""
    path = tmp_path / "tiny.pdf"
    doc = pymupdf.open()
    # 第 1 页
    page = doc.new_page()
    page.insert_text((72, 100), "?265.*chance /tSO:ns/ n.机会", fontname="china-s", fontsize=11)
    page.insert_text((72, 130), "G7上U2 We should improve ourselves.", fontname="china-s", fontsize=11)
    page.insert_text((72, 160), "我们应该抓住每一个机会。", fontname="china-s", fontsize=11)
    # 第 2 页
    page2 = doc.new_page()
    page2.insert_text((72, 100), "12", fontname="china-s", fontsize=11)
    doc.save(path)
    doc.close()
    return path


class TestExtractPages:
    def test_returns_all_pages(self, tiny_pdf):
        pages = extract_pages(tiny_pdf)
        assert len(pages) == 2

    def test_page_record_structure(self, tiny_pdf):
        pages = extract_pages(tiny_pdf)
        p = pages[0]
        assert p["page"] == 1  # 1-based 页码
        assert "chance" in p["text"]
        assert isinstance(p["lines"], list)

    def test_lines_have_y_and_text(self, tiny_pdf):
        p = extract_pages(tiny_pdf)[0]
        assert all(set(line) == {"y", "text"} for line in p["lines"])
        texts = [line["text"] for line in p["lines"]]
        assert any("chance" in t for t in texts)
        assert any("我们应该" in t for t in texts)

    def test_lines_in_reading_order(self, tiny_pdf):
        p = extract_pages(tiny_pdf)[0]
        texts = [line["text"] for line in p["lines"]]
        assert texts.index("G7上U2 We should improve ourselves.") < texts.index(
            "我们应该抓住每一个机会。"
        )
