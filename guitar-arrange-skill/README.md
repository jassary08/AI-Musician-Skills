# Guitar Arrange Skill

这个 skill 用自然语言生成可弹的吉他和声编配。它会从用户描述中推断风格、调性、难度、是否使用变调夹、和弦色彩，并选择适合吉他的 capo、play-as chords 和左手指法。

## 入口

只保留一个主入口：

```bash
python scripts/compose_guitar.py '写一段温暖的 C 大调流行副歌，适合初学者吉他弹唱，不要横按' --pretty
```

用户不需要准备结构化输入。自动化场景仍可传 JSON，但推荐 JSON 里只放自然语言 `request`。

## 典型使用场景

### 1. 新手弹唱和弦编配

用户说：

```text
写一段温暖的 C 大调流行副歌，适合初学者吉他弹唱，不要横按
```

skill 会生成适合弹唱的流行和弦进行，优先开放和弦，避免 F、Bm 这类新手困难横按，并输出 capo、指法、练习提示和 ChordPro。

### 2. 已有和弦进行改成更顺手的吉他版本

用户说：

```text
把 A E F#m D 这组和弦改成更适合新手弹唱的吉他版本，可以用变调夹
```

skill 会识别用户给出的和弦，尝试通过 capo 转成更好按的 play-as chords，并为每个和弦选择具体 frets、fingers、barres。

### 3. Blues 十二小节

用户说：

```text
写一段 E 小调经典 blues 十二小节，常用吉他弹法，不用变调夹
```

skill 会生成 blues 语境下的十二小节和声，保持 no-capo 策略，优先选择常见吉他 blues 指法和七和弦色彩。

### 4. 已有和弦进行改成 R&B / Neo-soul 色彩

用户说：

```text
把 C Am F G 这组和弦改成 R&B 色彩，给出我安排好的和弦指法图，不要变调夹，进阶弹法
```

skill 会识别用户给出的原始和弦进行，在保留基本功能走向的前提下加入 maj7、m7、9、sus 等 R&B 色彩，并选择更适合中级演奏者的小型 voicing。

### 5. 生成和弦图 PNG

```bash
python scripts/compose_guitar.py '写一段适合女生弹唱的 G 大调民谣主歌，可以用 capo' --diagram-png-output /tmp/chordcraft-diagrams.png --pretty
```

输出 JSON 的同时，会把选中的和弦指法渲染成 PNG 和弦图。

### 6. 导出练习材料

```bash
python scripts/compose_guitar.py '写一段 funk 吉他和弦，短促一点，难度中等' --export-dir /tmp/chordcraft-export --pretty
```

会生成：

- `arrangement.json`
- `lead_sheet.json`
- `practice_sheet.txt`
- `arrangement.cho`
- `voicing_summary.json`

## 当前脚本

- `scripts/compose_guitar.py`: 自然语言规划、capo 选择、和弦指法安排的唯一主入口。
- `scripts/render_chord_diagrams.py`: 从编配结果渲染 PNG 和弦图。
- `scripts/validate_rules.py`: 校验规则、风格卡和 voicing 资源是否完整。

## 数据边界

运行时主要使用：

- `resources/voicing_db/source/chords_db_voicings.json`: 原始吉他指法候选库。
- `resources/voicing_db/overlays/commonness_annotations.json`: 常用度、风格、状态等评分补充。
- `resources/style_cards/*.json`: 风格规则。
- `resources/rules/*.json`: capo、voicing、简化、校验、练习提示规则。

`resources/voicing_db/indexes/` 是随 release 保留的检查索引，不是当前运行时的主数据源。
