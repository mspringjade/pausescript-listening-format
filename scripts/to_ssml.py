#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把「英语听力试卷文本格式」转换成 SSML。

只做文本结构 -> SSML 结构的转换，不调用任何 TTS 或付费 API；合成交给任意
支持 SSML 的语音服务（Azure、Google、Amazon Polly、本地引擎等）。

运行：
    python3 scripts/to_ssml.py examples/c-passage.txt -o passage.ssml

依赖：Python 3.8+，只用标准库。
"""

import argparse
import re
import sys
from xml.sax.saxutils import escape

# --------------------------------------------------------------------------
# 识别规则：与 spec.md 中的表格一一对应
# --------------------------------------------------------------------------

SECTION_RE = re.compile(
    r"^(?:"
    r"[一二三四五六七八九十]+\s*[、．.]"      # 一、 二、 三.
    r"|第[一二三四五六七八九十]+\s*节"        # 第一节
    r"|Part\s+(?:[IVXLC]+|[A-Z]|\d+)"       # Part I / Part A / Part 1
    r"|Section\s+[A-Za-z]"                  # Section A
    r"|听第\s*\d+\s*段"                      # 听第 1 段对话……
    r"|听下面"                               # 听下面一段独白……
    r"|听一段"                               # 听一段对话……
    r")"
)

# 行首阿拉伯数字 + 英文句点 / 中文顿号 / 右括号；数字后紧跟数字时不算题号（避免 1.5 误判）
ITEM_RE = re.compile(r"^(\d{1,3})\s*[、．.)）](?!\d)\s*(.+)$")

# 单字母角色 + 冒号（中英文冒号均可）：M/A = 男声，W/B = 女声
TURN_RE = re.compile(r"^([MWAB])\s*[:：]\s*(.+)$", re.IGNORECASE)

# 大题说明里的遍数声明：读两遍 / 念 2 遍 / 朗读三遍
REPEAT_RE = re.compile(r"(?:读|念|朗读)\s*([一两二三四五\d]+)\s*遍")

CN_NUM = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
          "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}

# 英文句末切分；避免拆开 Mr. / Dr. 之外的缩写靠保守的前瞻（下一个字符大写或引号）
SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[\"'(\[]?[A-Z0-9])")
ZH_SENT_SPLIT_RE = re.compile(r"(?<=[。！？])")

# 句末切分时不算句末的常见缩写（小写比较）
ABBREVIATIONS = ("mr.", "mrs.", "ms.", "dr.", "prof.", "st.", "jr.", "sr.",
                 "vs.", "e.g.", "i.e.", "a.m.", "p.m.")

MALE_ROLES = {"M", "A"}
FEMALE_ROLES = {"W", "B"}

SAMPLE = "  <s>{}</s>"


# --------------------------------------------------------------------------
# 数据结构
# --------------------------------------------------------------------------

class Block:
    """一段已经分类好的内容。kind = section | item | turn | passage"""

    __slots__ = ("kind", "text", "number", "role", "repeat", "paragraphs")

    def __init__(self, kind, text="", number=None, role="", repeat=1, paragraphs=None):
        self.kind = kind
        self.text = text
        self.number = number
        self.role = role
        self.repeat = repeat
        self.paragraphs = paragraphs or []


def parse_duration(value):
    """'5s' / '5' / '800ms' / '2秒' -> 毫秒整数"""
    raw = str(value).strip().lower().replace(" ", "")
    m = re.fullmatch(r"(\d+(?:\.\d+)?)(ms|毫秒|s|秒|m|分)?", raw)
    if not m:
        raise argparse.ArgumentTypeError("无法识别的时长：{!r}（示例：5s、800ms）".format(value))
    num = float(m.group(1))
    unit = m.group(2) or "s"
    if unit in ("ms", "毫秒"):
        return int(num)
    if unit in ("m", "分"):
        return int(num * 60000)
    return int(num * 1000)


# --------------------------------------------------------------------------
# 解析
# --------------------------------------------------------------------------

def detect_repeat(line, default):
    m = REPEAT_RE.search(line)
    if not m:
        return default
    token = m.group(1)
    if token.isdigit():
        count = int(token)
    else:
        count = CN_NUM.get(token, default)
    return max(1, min(count, 5))


def parse(text, default_repeat):
    blocks = []
    repeat = default_repeat
    paragraph = []

    def flush_paragraph():
        if paragraph:
            blocks.append(Block("passage", paragraphs=list(paragraph), repeat=repeat))
            del paragraph[:]

    for raw in text.splitlines():
        line = raw.replace("\ufeff", "").strip()
        if not line:
            flush_paragraph()          # 空行只表示段落断开，不产生朗读内容
            continue

        if SECTION_RE.match(line):
            flush_paragraph()
            repeat = detect_repeat(line, default_repeat)
            blocks.append(Block("section", text=line))
            continue

        m = ITEM_RE.match(line)
        if m:
            flush_paragraph()
            number, body = int(m.group(1)), m.group(2).strip()
            inner = TURN_RE.match(body)   # 兼容「1. M: ...」这种把题号和对白写在一行的情况
            if inner:
                role = "male" if inner.group(1).upper() in MALE_ROLES else "female"
                blocks.append(Block("item", text=inner.group(2).strip(), number=number,
                                    role=role, repeat=repeat))
            else:
                blocks.append(Block("item", text=body, number=number, repeat=repeat))
            continue

        m = TURN_RE.match(line)
        if m:
            flush_paragraph()
            role = "male" if m.group(1).upper() in MALE_ROLES else "female"
            blocks.append(Block("turn", text=m.group(2).strip(), role=role))
            continue

        paragraph.append(line)

    flush_paragraph()
    return blocks


# --------------------------------------------------------------------------
# SSML 输出
# --------------------------------------------------------------------------

def split_sentences(text, lang):
    if lang == "zh":
        return [p.strip() for p in ZH_SENT_SPLIT_RE.split(text) if p.strip()]
    pieces = []
    for piece in SENT_SPLIT_RE.split(text):
        tail = pieces[-1].rstrip().lower() if pieces else ""
        # Mr. / Mrs. / Ms. / Dr. 这类缩写后面不切句
        if pieces and len(tail) <= 30 and tail.endswith(ABBREVIATIONS):
            pieces[-1] = pieces[-1].rstrip() + " " + piece
        else:
            pieces.append(piece)
    return [p.strip() for p in pieces if p.strip()]


class Builder:
    """把内容块写成 SSML；相邻且同音色的 <s> 合并进同一个 <voice>。"""

    def __init__(self, opts):
        self.opts = opts
        self.lines = []
        self._role = None
        self._open = False

    def _voice_name(self, role):
        if role == "zh":
            return self.opts.zh_voice
        if role == "male":
            return self.opts.male_voice
        return self.opts.female_voice

    def _close(self):
        if self._open:
            self.lines.append("  </voice>")
            self._open = False
            self._role = None

    def say(self, role, text):
        if not text:
            return
        if role != self._role:
            self._close()
            self.lines.append('  <voice name="{}">'.format(self._voice_name(role)))
            self._open = True
            self._role = role
        for piece in split_sentences(text, role):
            inner = escape(piece)
            if abs(self.opts.rate - 1.0) > 1e-6:
                pct = int(round(self.opts.rate * 100))
                inner = '<prosody rate="{}%">{}</prosody>'.format(pct, inner)
            self.lines.append("    <s>{}</s>".format(inner))

    def pause(self, ms):
        if ms <= 0:
            return
        tag = '<break time="{}ms"/>'.format(int(ms))
        self.lines.append(("    " if self._open else "  ") + tag)

    def render(self, blocks):
        o = self.opts
        for b in blocks:
            if b.kind == "section":
                self.say("zh", b.text)
                self.pause(o.section_gap)
            elif b.kind == "turn":
                self.say(b.role, b.text)
                self.pause(o.turn_gap)
            elif b.kind == "item":
                item_voice = b.role or o.item_voice
                if o.number_style != "none":
                    word = "Question" if o.number_style == "question" else "Number"
                    self.say(item_voice, "{} {}.".format(word, b.number))
                    self.pause(o.number_gap)
                for i in range(max(1, b.repeat)):
                    if i:
                        self.pause(o.repeat_gap)
                    if b.text:
                        self.say(item_voice, b.text)
                self.pause(o.answer_pause)
            elif b.kind == "passage":
                for rep in range(max(1, b.repeat)):
                    if rep:
                        self.pause(o.repeat_gap)
                    for idx, para in enumerate(b.paragraphs):
                        if idx:
                            self.pause(o.paragraph_gap)
                        self.say(o.passage_voice, para)
                self.pause(o.paragraph_gap)
        self._close()

        head = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">',
        ]
        return "\n".join(head + self.lines + ["</speak>", ""])


# --------------------------------------------------------------------------
# 命令行
# --------------------------------------------------------------------------

def main(argv=None):
    p = argparse.ArgumentParser(
        description="把英语听力试卷文本格式转换成 SSML（纯标准库，不调用任何 API）",
        epilog="运行：python3 scripts/to_ssml.py examples/c-passage.txt -o passage.ssml",
    )
    p.add_argument("input", nargs="?", default="-", help="输入文本文件；省略或 - 表示读标准输入")
    p.add_argument("-o", "--output", help="输出文件；省略则打印到标准输出")
    p.add_argument("--answer-pause", type=parse_duration, default=parse_duration("5s"),
                   help="每题读完后的答题停顿，默认 5s")
    p.add_argument("--repeat", type=int, default=2,
                   help="默认朗读遍数，默认 2；大题说明里的「读两遍」会覆盖它")
    p.add_argument("--repeat-gap", type=parse_duration, default=parse_duration("1.5s"),
                   help="同一内容两遍之间的停顿，默认 1.5s")
    p.add_argument("--section-gap", type=parse_duration, default=parse_duration("1s"),
                   help="大题说明播完后的停顿，默认 1s")
    p.add_argument("--turn-gap", type=parse_duration, default=parse_duration("250ms"),
                   help="对白每轮之间的停顿，默认 250ms")
    p.add_argument("--number-gap", type=parse_duration, default=parse_duration("400ms"),
                   help="题号播报与正文之间的停顿，默认 400ms")
    p.add_argument("--paragraph-gap", type=parse_duration, default=parse_duration("600ms"),
                   help="短文段落之间的停顿，默认 600ms")
    p.add_argument("--number-style", choices=["question", "number", "none"], default="question",
                   help="题号播报形式：Question N / Number N / 不播报，默认 question")
    p.add_argument("--item-voice", choices=["male", "female"], default="female",
                   help="题号与单句默认音色，默认 female")
    p.add_argument("--passage-voice", choices=["male", "female"], default="female",
                   help="短文朗读音色，默认 female")
    p.add_argument("--male-voice", default="en-US-GuyNeural", help="男声 name 属性")
    p.add_argument("--female-voice", default="en-US-JennyNeural", help="女声 name 属性")
    p.add_argument("--zh-voice", default="zh-CN-XiaoxiaoNeural", help="中文大题说明音色")
    p.add_argument("--rate", type=float, default=1.0,
                   help="语速倍率，如 0.9；不等于 1 时输出 prosody 标签")
    opts = p.parse_args(argv)

    if opts.input in ("-", None):
        text = sys.stdin.read()
    else:
        with open(opts.input, "r", encoding="utf-8-sig") as fh:
            text = fh.read()

    if not text.strip():
        p.error("输入文本为空")

    blocks = parse(text, max(1, opts.repeat))
    ssml = Builder(opts).render(blocks)

    if opts.output:
        with open(opts.output, "w", encoding="utf-8") as fh:
            fh.write(ssml)
        print("已写入 {}（{} 个内容块）".format(opts.output, len(blocks)), file=sys.stderr)
    else:
        sys.stdout.write(ssml)
    return 0


if __name__ == "__main__":
    sys.exit(main())
