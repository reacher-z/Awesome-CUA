from html.parser import HTMLParser
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from search_pages import DESCRIPTION_CONTEXT, clip, description, meta_description, page, page_title, resource_context, resource_path

ROOT=Path(__file__).resolve().parents[1]


class MetaParser(HTMLParser):
    def __init__(self,text):
        super().__init__();self.meta={}
        self.feed(text.split('</head>',1)[0])
    def handle_starttag(self,tag,attrs):
        a=dict(attrs);key=a.get('name') or a.get('property')
        if tag=='meta' and key in {'description','og:description'}:self.meta[key]=a['content']


class ClipTests(unittest.TestCase):
    def assertWholeWordClip(self,text,clipped,limit=300):
        self.assertLessEqual(len(clipped),limit);self.assertTrue(clipped.endswith('…'),clipped)
        kept=clipped[:-1];self.assertTrue(text.startswith(kept));self.assertFalse(kept[-1].isspace())
        self.assertTrue(text[len(kept)].isspace() or text[len(kept)] in ',;:.',text[len(kept)-10:len(kept)+10])
    def test_short_and_exact_length_text_is_unchanged(self):
        self.assertEqual(clip('A short summary.'),'A short summary.')
        exact=('word '*60)[:299]+'x';self.assertEqual(len(exact),300);self.assertEqual(clip(exact),exact)
    def test_long_text_is_cut_at_a_word_boundary_with_an_ellipsis(self):
        text='Introduces Sidekick. '+'A user study examines progress awareness, error traceability, and multitasking across background and foreground work. '*3
        self.assertGreater(len(text),300);self.assertWholeWordClip(text,clip(text))
        self.assertNotIn('foreground w…',clip(text))
    def test_word_ending_just_before_the_limit_is_kept(self):
        text='a'*298+' bb';self.assertEqual(clip(text),'a'*298+'…')
        text='a'*296+' bb cc';self.assertEqual(clip(text),'a'*296+' bb…')
    def test_trailing_punctuation_is_not_left_before_the_ellipsis(self):
        self.assertEqual(clip('alpha, beta, gamma',limit=14),'alpha, beta…')
    def test_text_without_whitespace_is_still_bounded(self):
        clipped=clip('x'*400);self.assertEqual(len(clipped),300);self.assertTrue(clipped.endswith('…'))
    def test_generated_meta_and_social_descriptions_stay_within_search_bounds(self):
        rows=[json.loads(line) for line in (ROOT/'data/catalog.jsonl').read_text().splitlines() if line.strip()]
        shortened=0
        for r in rows:
            text=description(r);meta=MetaParser(page(r['name'],text,resource_path(r),'<h1>x</h1>',context=resource_context(r))).meta
            with self.subTest(id=r['id']):
                self.assertEqual(meta['description'],meta['og:description'])
                self.assertTrue(70<=len(meta['description'])<=160,(len(meta['description']),meta['description']))
                self.assertFalse(meta['description'][-1].isspace())
                if len(text)>160:
                    shortened+=1
                    if meta['description'].endswith('…'):self.assertWholeWordClip(text,meta['description'],160)
                    else:self.assertTrue(text.startswith(meta['description']))
                elif len(text)>=70:self.assertEqual(meta['description'],' '.join(text.split()))
        self.assertGreater(shortened,0)
    def test_short_summaries_gain_context_and_chinese_uses_its_own_bounds(self):
        self.assertEqual(meta_description('A short summary.'),'A short summary. '+DESCRIPTION_CONTEXT['en'])
        chinese=meta_description('提出 WebNav。',lang='zh-CN')
        self.assertTrue(50<=len(chinese)<=160,chinese)
        long='这是一个很长的中文摘要，'*30
        clipped=meta_description(long,lang='zh-CN')
        self.assertLessEqual(len(clipped),160);self.assertTrue(clipped.endswith('…'))
    def test_whole_sentences_are_kept_when_they_fit(self):
        text='First sentence describes the benchmark in enough words to be useful for search results today. '+'Second sentence adds far more detail than a snippet can hold, '*4
        self.assertEqual(meta_description(text),text.split('. ')[0]+'.')
    def test_titles_fit_sixty_characters_with_the_brand(self):
        self.assertEqual(page_title('OSWorld'),'OSWorld | AwesomeCUA')
        long=page_title('A Survey on (M)LLM-Based GUI Agents: Foundations, Technologies and Challenges')
        self.assertLessEqual(len(long),60);self.assertTrue(long.endswith('… | AwesomeCUA'))
        self.assertLessEqual(len(page_title('计算机使用智能体资源目录：'*8)),60)

if __name__=='__main__':unittest.main()
