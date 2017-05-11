import sqlite3
from itertools import chain, combinations
import random
import time

class crossword:
    def __init__(self,dbname,gridsize):
            self.grid=[['_' for l in range(gridsize)] for i in range(gridsize)]
            self.bars=[[['H','V'] for l in range(gridsize)] for i in range(gridsize)]
            self.keyv=[]
            self.keyh=[]
            self.gridsize=gridsize
            self.allWords=[]
            self.order=[]
            self.mergekey=[]
            stdsize=self.gridsize-1
            i=0
            while i<(stdsize)/2:
                self.order.extend([str(i)+'H',str(i)+'V',str(stdsize-i)+'H',str(stdsize-i)+'V'])
                i+=2
            if (stdsize/2)%2==0:
                self.order.extend([str(i)+'H',str(i)+'V'])
            i=1
            while i<(stdsize)/2:
                self.order.extend([str(i)+'H',str(i)+'V',str(stdsize-i)+'H',str(stdsize-i)+'V'])
                i+=2            
            self.dbname=dbname
            self.conn=sqlite3.connect(self.dbname)
            self.c=self.conn.cursor()
        
    def ordercreate(self):
        gridsize=self.gridsize-1
        i=0
        while i<(gridsize)/2:
            self.order.extend([str(i)+'H',str(i)+'V',str(gridsize-i)+'H',str(gridsize-i)+'V'])
            i+=2
        if (gridsize/2)%2==0:
            self.order.extend([str(i)+'H',str(i)+'V'])
        i=1
        while i<(gridsize)/2:
            self.order.extend([str(i)+'H',str(i)+'V',str(gridsize-i)+'H',str(gridsize-i)+'V'])
            i+=2

    def mergekeycreate(self):
        for i,moveh in enumerate(self.keyh):
            self.mergekey.append({'P':moveh[0],'H':moveh[1]})
            for l,movev in enumerate(self.keyv):
                if movev[0]==moveh[0]:
                    self.mergekey[-1]['V']=movev[1]
                    del self.keyv[l]
        for movev in self.keyv:
            self.mergekey.append({'P':movev[0],'V':movev[1]})
        del self.keyh,self.keyv
        

    def cwcreate(self):
        
        for move in self.order:
            move=allocation(int(move[:-1]),move[-1],self.grid,self.bars,self.keyh,self.keyv,self.c,self.allWords)
            move.__main__()
            self.grid=move.grid
            self.bars=move.bars
            self.keyh=move.keyh
            self.keyv=move.keyv
            self.allWords.extend(move.line)
        self.mergekeycreate()

class allocation(crossword):
    def __init__(self,linenum,alignment,grid,bars,keyh,keyv,dbcursor,allWords):
        self.linenum=linenum
        self.alignment=alignment
        self.variations=[]
        self.line=[]
        self.grid=grid
        self.bars=bars
        self.keyh=keyh
        self.keyv=keyv
        self.c=dbcursor
        self.allWords=allWords
        #super().__init__(dbname,gridsize)
    
    @staticmethod
    def sliceable(xs):
        try:
            xs[:0]
            return xs
        except TypeError:
            return tuple(xs)

    def partition(self, iterable):
        s = self.sliceable(iterable)
        n = len(s)
        b, mid, e = [0], list(range(1, n)), [n]
        getslice = s.__getitem__
        splits = (d for i in range(n) for d in combinations(mid, i))
        return [[s[sl] for sl in map(slice, chain(b, d), chain(d, e))]
                for d in splits]

    def getvars(self):
        line=[]
        if self.alignment=='H':
            line=''.join(self.grid[self.linenum])
        elif self.alignment=='V':
            line=''.join([i[self.linenum] for i in self.grid])
        self.variations=[part for part in self.partition (line) if len(min(part,key=len))>1]
        random.shuffle(self.variations)

    def getword(self,struct):
        self.c.execute("SELECT formatted FROM dictionary WHERE formatted LIKE (?)",(struct,))
        words=[item[0] for item in self.c.fetchall() if item[0] not in self.allWords]
        return words

    def query(self):
        for var in self.variations:
            tempQuery=[]
            for subvar in var:
                try:
                    tempQuery.append(random.choice(self.getword(subvar)))
                except IndexError:
                    continue
            if len(tempQuery)==len(var):
                self.line=tempQuery
            continue

    def gridalloc(self):
        templist=[]
        [templist.extend(list(word)) for word in self.line]
        if self.alignment=='H' and len(templist)>0:
            self.grid[self.linenum]=templist
        elif self.alignment=='V':
            for i,char in enumerate(templist):
                self.grid[i][self.linenum]=char

    def barsalloc(self):
        if len(self.line)>0:
            stillBarred=[len(''.join(self.line[:i])) for i in range(1,len(self.line)+1)]
            if self.alignment=='H':
                for i,bar in enumerate(self.bars[self.linenum]):
                    try:
                        if i+1 not in stillBarred:
                            bar.remove('H')
                    except ValueError:
                        print('error')
                        continue
            elif self.alignment=='V':
                for i,line in enumerate(self.bars):
                    try:
                        if i+1 not in stillBarred:
                            line[self.linenum].remove('V')
                    except ValueError:
                        print('error')
                        continue

    def keyalloc(self):
        if self.alignment=='H':
            for i,option in enumerate(self.line):
                self.c.execute('SELECT definition FROM dictionary WHERE formatted==(?)',(option,))
                definition=self.c.fetchone()
                definition=definition[0].replace('\xa0',' ')
                self.keyh.append([[(len(''.join(self.line[:i]))),self.linenum],definition])
        elif self.alignment=='V':
            for i,option in enumerate(self.line):
                self.c.execute('SELECT definition FROM dictionary WHERE formatted==(?)',(option,))
                definition=self.c.fetchone()
                definition=definition[0].replace('\xa0',' ')
                self.keyv.append([[self.linenum,(len(''.join(self.line[:i])))],definition])

    def __main__(self):
        self.getvars()
        self.query()
        self.gridalloc()
        self.barsalloc()
        self.keyalloc()

from bidi.algorithm import get_display
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_RIGHT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Frame, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.utils import simpleSplit
from reportlab.rl_config import defaultPageSize
from reportlab.lib.colors import *

class pdfgen:
    
    def __init__(self,crossword,savename):
        self.key=crossword.mergekey
        self.bars=crossword.bars
        self.c=canvas.Canvas(savename)
        #self.c.save()
        pdfmetrics.registerFont(TTFont('David','DavidCLM-Medium.ttf'))
        self.styles={'default':ParagraphStyle('default',fontSize=8,fontName='David',alignment=TA_RIGHT),
                     'subtitle':ParagraphStyle('subtitle',fontSize=11,fontName='David',alignment=TA_RIGHT,spaceAfter=5)}
        self.keyStyle=self.styles['default']
        self.keyh=[Paragraph('<u>ןזואמ</u>',self.styles['subtitle'])]
        self.keyv=[Paragraph('<u>ךנואמ</u>',self.styles['subtitle'])]
        self.gridsize=crossword.gridsize
        self.tableData=[['' for l in range(crossword.gridsize)] for i in range(crossword.gridsize)]
        self.tableStyle=TableStyle([('FONT',(0,0),(-1,-1),'David'),
                                    ('ALIGN',(0,0),(-1,-1),'RIGHT'),
                                    ('FONTSIZE',(0,0),(-1,-1),9),
                                    ('VALIGN',(0,0),(-1,-1),'TOP'),
                                    ('BOX',(0,0),(-1,-1),0.7,black),
                                    ('GRID',(0,0),(-1,-1),0.7,black)])
        self.table=None
        
    def pdfkeycreate(self):
        for i,intersection in enumerate(self.key):
            try:
                temph=simpleSplit((intersection['H']),'David',8,3.9*cm)
                #temph.reverse()
                temph[0]=((temph[0][::-1]+"."+str(i+1)))
                self.keyh.append(Paragraph(temph[0],self.styles['default']))
                for item in temph[1:]:
                        self.keyh.append(Paragraph((item[::-1]),self.styles['default']))
            except KeyError:
                pass
            try:
                tempv=simpleSplit((intersection['V']),'David',8,3.9*cm)
                tempv[0]=((tempv[0][::-1]+"."+str(i+1)))
                self.keyv.append(Paragraph(tempv[0],self.styles['default']))
                for item in tempv[1:]:
                    self.keyv.append(Paragraph((item[::-1]),self.styles['default']))
            except KeyError:
                pass

    def tableDataCreate(self):
        for i,intersection in enumerate(self.key):
            self.tableData[intersection['P'][1]][self.gridsize-1-intersection['P'][0]]=i+1

    def tableStyleCreate(self):
        for i,line in enumerate(self.bars):
            for l,bar in enumerate(line):
                if ('H' in bar) and ('V' in bar) and ('V' in self.bars[i-1][l]) and ('H' in self.bars[i][l-1]):
                    self.tableStyle.add('BACKGROUND',(self.gridsize-1-l,i),(self.gridsize-1-l,i),black)
                if 'H' in bar:
                    self.tableStyle.add('LINEBEFORE',(self.gridsize-1-l,i),(self.gridsize-1-l,i),1.6,black)
                if 'V' in bar:
                    self.tableStyle.add('LINEBELOW',(self.gridsize-1-l,i),(self.gridsize-1-l,i),1.6,black)
                

    def tableCreate(self):
        self.table=Table(self.tableData,colWidths=1.2*cm,rowHeights=1.2*cm,style=self.tableStyle)        
            
    def keydraw(self):
        hFrame1=Frame(15.45*cm,1*cm,4.75*cm,11.5*cm)
        hFrame2=Frame(10.55*cm,1*cm,4.75*cm,11.5*cm)
        hFrame1.addFromList(self.keyh[:26],self.c)
        hFrame2.addFromList(self.keyh[26:],self.c)
        vFrame1=Frame(5.7*cm,1*cm,4.75*cm,11.5*cm)
        vFrame2=Frame(0.8*cm,1*cm,4.75*cm,11.5*cm)
        vFrame1.addFromList(self.keyv[:26],self.c)
        vFrame2.addFromList(self.keyv[26:],self.c)
        tFrame=Frame(0.8*cm,11.3*cm,19.4*cm,16.1*cm,showBoundary=1)
        tFrame.add(self.table,self.c)
        self.c.drawCentredString(10.5*cm,28.4*cm,'Created with WordCrusader by Yotam Hochman')
        
        self.c.save()
        
import tkinter
import tkinter.filedialog
import tkinter.messagebox

def main(gridsize):
    savepath=tkinter.filedialog.asksaveasfilename(filetypes = (("Portable Document Format", "*.pdf")
                                                         , ), defaultextension='.pdf')
    start_time=time.time()
    instance=crossword('hebrew.db',gridsize)
    instance.cwcreate()
    pdf=pdfgen(instance,savepath)
    pdf.pdfkeycreate()
    pdf.tableDataCreate()
    pdf.tableStyleCreate()
    pdf.tableCreate()
    pdf.keydraw()
    tkinter.messagebox.showinfo('Done','Puzzle created successfully, {} words in {} seconds'.format(len(instance.allWords),str(round(time.time()-start_time,2))))
    

gui=tkinter.Tk()
gui.title('WordCrusader 1.0')
scale=tkinter.Scale(gui,from_=5,to=12,label='Choose Grid Size:',orient=tkinter.HORIZONTAL,
                    length=280,width=35)
scale.set(10)
scale.pack()

crusadeb=tkinter.Button(gui,command=lambda: main(scale.get()),text='Crusade!')
crusadeb.pack(side=tkinter.BOTTOM)


