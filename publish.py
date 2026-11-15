#!/usr/bin/env python3
"""Usage: publish.py report.md  -> rewrites feed.xml with only this report, commits and pushes."""
import sys,re,html,email.utils,datetime,subprocess,zoneinfo,os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
md=open(sys.argv[1],encoding='utf-8').read()
def inline(s):
    s=html.escape(s,quote=False)
    s=re.sub(r'\*\*(.+?)\*\*',r'<b>\1</b>',s)
    s=re.sub(r'\[([^\]]+)\]\(([^)]+)\)',r'<a href="\2">\1</a>',s)
    return s
out=[];inl=False
for l in md.split('\n'):
    l=l.rstrip()
    if re.match(r'#{1,6} ',l):
        if inl: out.append('</ul>');inl=False
        out.append('<h2>'+inline(l.lstrip('#').strip())+'</h2>')
    elif re.match(r'[-*] ',l):
        if not inl: out.append('<ul>');inl=True
        out.append('<li>'+inline(l[2:])+'</li>')
    elif l.strip():
        if inl: out.append('</ul>');inl=False
        out.append('<p>'+inline(l)+'</p>')
if inl: out.append('</ul>')
body='\n'.join(out).replace(']]>',']]&gt;')
now=datetime.datetime.now(zoneinfo.ZoneInfo('Europe/Madrid'))
pub=email.utils.format_datetime(now)
dani=['ponedeljak','utorak','sreda','četvrtak','petak','subota','nedelja']
title=f"Jutarnji izveštaj Srbija – {dani[now.weekday()]}, {now.day}. {now.month}. {now.year}."
xml=f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">
<channel>
<title>Jutarnji izveštaj Srbija</title>
<link>https://icemonk79.github.io/srbija-rss/</link>
<description>Dnevni pregled politike, zakona, cena, poreza i komunalija u Srbiji</description>
<language>sr</language>
<lastBuildDate>{pub}</lastBuildDate>
<item>
<title>{html.escape(title)}</title>
<link>https://icemonk79.github.io/srbija-rss/</link>
<guid isPermaLink="false">srbija-izvestaj-{now:%Y-%m-%d-%H%M}</guid>
<pubDate>{pub}</pubDate>
<description><![CDATA[{body}]]></description>
<content:encoded><![CDATA[{body}]]></content:encoded>
</item>
</channel>
</rss>
'''
from xml.dom import minidom as _minidom; _minidom.parseString(xml.encode())
open('feed.xml','w',encoding='utf-8').write(xml)
g=['git','-c','user.name=icemonk79','-c','user.email=icemonk79@users.noreply.github.com']
subprocess.run(['git','pull','-q','--rebase'],check=False)
subprocess.run(['git','add','feed.xml'],check=True)
subprocess.run(g+['commit','-qm',title],check=False)
subprocess.run(['git','push','-q'],check=True)
print('published',title)
