"""English and Chinese labels for publication-record and structured-profile fields, shared by the HTML pages and the Markdown twins."""
from __future__ import annotations

FIELD_LABELS = {
    # Publication record
    'title': ('Title', '标题'),
    'authors': ('Authors', '作者'),
    'venue': ('Venue', '发表于'),
    'publisher': ('Publisher', '出版方'),
    'series': ('Series', '丛书'),
    'volume': ('Volume', '卷'),
    'issue': ('Issue', '期'),
    'pages': ('Pages', '页码'),
    'doi': ('DOI', 'DOI'),
    'date_basis': ('Date source', '日期来源'),
    'event_dates': ('Event dates', '会议日期'),
    'identity_basis': ('Identity basis', '版本对应依据'),
    'notes': ('Source notes', '来源备注'),
    # Benchmark protocol
    'focus': ('Focus', '侧重'),
    'setting': ('Setting', '任务设置'),
    'observations': ('Observations', '观测'),
    'actions': ('Actions / outputs', '动作 / 输出'),
    'evaluation': ('Evaluation', '评测方式'),
    # Dataset profile
    'supervision': ('Supervision', '监督信号'),
    'modalities': ('Modalities', '模态'),
    'formats': ('Formats', '格式'),
    'splits': ('Splits', '数据划分'),
}

COUNT_BASIS = {'reported': ('reported', '来源报告'), 'computed': ('computed', '计算得出')}


def field_label(key, language='en'):
    english, chinese = FIELD_LABELS[key]
    return chinese if language == 'zh' else english
