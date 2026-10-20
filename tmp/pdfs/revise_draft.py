from pathlib import Path
from io import BytesIO
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from PIL import Image, ImageDraw, ImageFont

root = Path('/Users/bryanlefranss/Documents/ChatGPT/python')
out = root / 'output/pdf/draf-usulan-revisi-pelanggaran.pdf'
out.parent.mkdir(parents=True, exist_ok=True)
reader = PdfReader('/Users/bryanlefranss/Downloads/txt.pdf')
buf = BytesIO()
c = canvas.Canvas(buf, pagesize=(595,842))
# Preserve the scan except for the requested list and clearly visible draft labels.
c.setFillColorRGB(1,1,1)
c.rect(190,157,362,139,fill=1,stroke=0)
c.setFillColorRGB(0,0,0)
c.setFont('Times-Bold',11.5)
c.drawString(193,284,'Pelanggaran yang dilakukan :')
style = ParagraphStyle('body',fontName='Times-Roman',fontSize=11.5,leading=15)
items = [
 'a. Saya melakukan kerja sama dengan Saudari Catherine Wijaya untuk melakukan plagiarisme terhadap paper Scopus Hope Mbelwa, dan Catherine memberikan uang sebesar Rp10.000.000 kepada Bryan.',
 'b. Adanya intensi penipuan paper terkait email yang telah disampaikan kepada Saudara Bryan.'
]
y=265
for text in items:
 p=Paragraph(text,style)
 _,h=p.wrap(331,150)
 p.drawOn(c,213,y-h)
 y-=h+10
c.setFillColorRGB(.52,.08,.08)
c.rect(36,809,523,25,fill=1,stroke=0)
c.setFillColorRGB(1,1,1)
c.setFont('Helvetica-Bold',11)
c.drawCentredString(297.5,818,'DRAF USULAN REVISI - BUKAN DOKUMEN RESMI')
c.saveState()
c.translate(297.5,440)
c.rotate(33)
c.setFillColorRGB(.6,.1,.1)
c.setFillAlpha(.22)
c.setFont('Helvetica-Bold',37)
c.drawCentredString(0,0,'DRAF - BUKAN DOKUMEN RESMI')
c.restoreState()
c.save()
page=reader.pages[0]
page.merge_page(PdfReader(buf).pages[0])
writer=PdfWriter()
writer.add_page(page)
writer.add_metadata({'/Title':'Draf usulan revisi - bukan dokumen resmi'})
with out.open('wb') as f: writer.write(f)
assert 'Rp10.000.000' in PdfReader(out).pages[0].extract_text()
print(out)
