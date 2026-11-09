# 英语听力试卷文本格式

一份纯文本的排版约定：把听力原文写成固定结构，任何 TTS 或解析脚本都能读懂，直接排出带中文大题说明、题号播报、男女对白和答题停顿的音频。

## 这个格式解决什么问题

同一套听力试卷，换个人排版就是另一种样子。题号有人写「1.」，有人写「1、」，有人写「第 1 题」；女声有人标记「W:」，有人写「女：」；大题说明有的单独一行，有的和首个题目挤在一起。人读都懂，程序读不懂——行首差一个标点，整段就被当成英文正文念出来，题号丢了，男女对白也变成一个人的独白。于是每做一套音频，等于把文本重新人工拆一遍。

这个仓库把「怎么写」固定下来，规则都落在行首：行首是什么标记，决定这一行由谁读、读几遍、读完停多久。文本本身仍然是纯文本，记事本、Word、Markdown 都能写；粘进任何支持 SSML 的语音服务或者自己的脚本，出来的结构是一致的。

我维护的在线工具是 [PauseScript 在线生成听力音频](https://pausescript.com)：整卷文本粘进去，自动识别大题说明、题号、男女对白与短文，按考场节奏留好停顿，导出 MP3。这里的规范就是它实际使用的排版约定，抽出来单独维护——老师照抄 `examples/` 改内容，开发者照 `spec.md` 写解析器。

## 试听一段生成结果

**[▶ 播放示例音频（32 秒，MP3，373 KB）](examples/sample-dialogue.mp3)**

链接指向仓库里的文件本身，点开就能在文件页试听，文件页右上角也有下载按钮。README 不支持内嵌 `<audio>`，所以这里给链接而不是播放器。

这 32 秒是从一份完整试卷的成品音频里截出来的，先后经过中文大题说明、小标题和三轮对白：

| 时间 | 听到的内容 | 来自哪种行 | 音色 |
| --- | --- | --- | --- |
| 0:00 | 二、听对话，根据对话内容，选择正确答案。每小题念两遍。 | 大题说明 | 中文女声 |
| 0:10 | 听第一段对话，回答第 1、2 题。 | 小标题，同样按大题说明处理 | 中文女声 |
| 0:17 | Hi, Mary. Are you ready for our science project presentation tomorrow? | `M:` 对白行 | 男声 |
| 0:24 | Almost, David. I've finished the slides but I need to double check the data. | `W:` 对白行 | 女声 |
| 0:30 | Take your time. | 又一行 `M:`，换回男声 | 男声 |

两点对着文字听时的说明：

- 音频里题号念的是 `Number N`，对应参数 `number_style = number`；不设这个参数时默认念 `Question N`。
- 第 1 行声明了「每小题念两遍」，示例只截了第一遍，第二遍紧接在这段之后。

## 格式规范总表

| 字段 | 含义 | 示例值 |
| --- | --- | --- |
| 大题说明（中文播报） | 整行以中文大题标记开头时，整行交给中文音色朗读，不切英文句，也不播报题号；同时为下面所有题目设定默认遍数 | `一、听下面三段对话，每段对话后有一个小题。` |
| 题号播报 | 行首阿拉伯数字加 `.` 或 `、`，数字被提取成题号单独念一遍（Question N / Number N，可关闭），正文从数字之后开始 | `6. When does the reading room close today?` |
| 单句播报（是否读两遍） | 这道题朗读的遍数。默认 2 遍；大题说明里写「读两遍」「读一遍」，该大题下所有条目跟着变 | `每个句子读两遍。` → 遍数 2 |
| 男女声交替 | 行首单字母加冒号决定音色，`M`/`A` 为男声，`W`/`B` 为女声；标记本身不朗读，逐行独立判定，不看上一行 | `W: Excuse me, ...`<br>`M: At half past five.` |
| 角色对白（A/B 轮次） | 一轮一行，音色只由字母决定（`A` 男声 / `B` 女声），与上一行无关，不要求交替；同一行里只能有一个人说话 | `A: ...`<br>`B: ...` |
| 短文朗读 | 大题说明含「短文」「独白」「朗读」时，紧随其后的无标记英文段落按整篇连读，不逐句播报题号；空行只分段，不产生朗读内容 | `三、听下面一段短文，……`<br>+ 连续英文段落 |
| 答题停顿时长 | 每题读完后留的空白秒数，属于渲染参数，不写进正文；常用值：单句听写 8 秒，短对话 5 秒，长对话与短文 8–10 秒 | `answer_pause = 5s` |

## 完整示例

`examples/c-passage.txt` 原文，可以直接粘贴使用：

```text
三、听下面一段短文，根据短文内容选择正确答案。短文读两遍。
Good morning, everyone. This is the school radio. Our yearly science fair will be held in the gym next Friday, from nine in the morning to four in the afternoon. Every class should prepare at least one project, and the top two projects will be shown again at the opening ceremony next month.
Students who want to join the fair should write their names on the notice board outside the science lab before Wednesday. If you need a table or a power socket for your project, please tell your science teacher two days in advance. Small tools and paper will be provided by the school, but you have to bring your own computer.
By the way, the gym will be closed this Wednesday afternoon, so the badminton club will meet in the playground instead. Thank you for listening, and have a nice day.
9. What is the speaker mainly talking about?
10. Where should students write their names?
11. Why will the badminton club meet in the playground?
```

同一份文本生成的音频结构（顺序与停顿，具体时长随语速变化）：

| # | 音频里听到的内容 | 来自哪一行 | 音色 | 之后的停顿 |
| --- | --- | --- | --- | --- |
| 1 | 三、听下面一段短文，根据短文内容选择正确答案。短文读两遍。 | 第 1 行，大题说明 | 中文女声 | 1 秒 |
| 2 | Good morning, everyone. …… have a nice day.（三段连读，段间 0.6 秒） | 第 2–4 行，短文段落 | 英文女声 | 1.5 秒 |
| 3 | 同上，整篇再读一遍 | 第 2–4 行 | 英文女声 | 1.5 秒 |
| 4 | Question 9. What is the speaker mainly talking about? | 第 5 行，题号行 | 英文女声 | 8 秒 |
| 5 | Question 10. Where should students write their names? | 第 6 行 | 英文女声 | 8 秒 |
| 6 | Question 11. Why will the badminton club meet in the playground? | 第 7 行 | 英文女声 | 8 秒 |

三处容易忽略的对应关系：

- 一个题号行会变成两句话。`9. What is...` 里的 `9.` 被剥出来单念成 `Question 9.`，后面才是题干本身，两者之间插一个短停顿（示例里 0.4 秒）。
- 「短文读两遍」既是给考生听的，也是给程序读的。程序从这句话里取到遍数 2，作用范围是本大题下的短文段落，所以第 2、3 行整体重复一次，不是每一段各读两次。
- 空行和换行不是朗读内容。短文按三行写还是并成一行写，听起来一样；只有空行会被当成段落边界，多留一点段间停顿。

## 怎么用这个格式

1. **改文本。** 从 `examples/` 里挑一份最接近的，保留行首标记不动，只换内容：每个题号单独一行，每轮对话单独一行，中文说明和英文正文不混行，选择题选项不要粘。
2. **生成音频。** 粘贴到工作台直接导出 MP3；或者本地跑脚本转成 SSML，再交给任意支持 SSML 的语音服务：

   ```bash
   python3 scripts/to_ssml.py examples/c-passage.txt -o passage.ssml
   ```

   脚本只用 Python 标准库，Python 3.8 以上即可，不联网、不调用付费接口。

3. **对着时间轴听一遍。** 重点查三件事：题号有没有被念进正文、对白有没有串成同一个声音、答题停顿够不够写完答案。改文本后重新生成，不必动设置。

## 常见问题

**选择题的选项要粘进去吗？**

不要。音频只读考生耳朵里听到的原文，`A. Yes, I do.` 这类选项印在卷面上给人看。粘进去会被当成正文朗读，多出一段没有人听的内容。

**题号会自动重排吗？**

不会。题号只用于播报，念的就是文本里写的数字，按出现顺序走。跨大题连续编号（6、7、8）需要自己在文本里写对；重复或跳号不会报错，会照原样念。

**中文和英文能写在同一行吗？**

不建议。一行只放一种语言：中文行按大题说明处理，英文行按句子或短文处理。混排时整行只会用其中一种语言的音色读，另一半的发音不可控。

## 仓库内容

```text
spec.md                        字段的完整取值规则与边界情况
examples/a-dictation.txt       单句听写
examples/b-dialogue.txt        男女对白
examples/c-passage.txt         短文朗读 + 答题停顿
examples/sample-dialogue.mp3   32 秒成品音频，即上面试听的那一段
scripts/to_ssml.py             纯标准库的格式转换脚本
LICENSE                        MIT
```

三份 `.txt` 示例均为通用题材自行编写，可直接用于教学，不涉及任何真题素材；示例音频另取自一份完整试卷，只用于演示格式效果。

## 许可

MIT，见 [LICENSE](LICENSE)。
