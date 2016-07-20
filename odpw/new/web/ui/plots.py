from collections import defaultdict

import numpy as np
from bokeh.models import NumeralTickFormatter, FuncTickFormatter, Text, Range1d, HoverTool, \
    ColumnDataSource, pd
from bokeh.plotting import figure
from numpy.ma import arange

from odpw.new.core.model import PortalSnapshotQuality, PortalSnapshot
from odpw.new.utils.utils_snapshot import getLastNSnapshots
from odpw.new.web.rest.odpw_restapi_blueprint import row2dict


ex={}
ex['ExAc']={'label': 'Access', 'color':'#311B92' }
ex['ExCo']={'label': 'Contact', 'color':'#4527A0'}
ex['ExDa']={'label': 'Date', 'color':'#512DA8'}
ex['ExDi']={'label': 'Discovery', 'color':'#5E35B1'}
ex['ExPr']={'label': 'Preservation', 'color':'#673AB7'}
ex['ExRi']={'label': 'Rights', 'color':'#7E57C2'}
ex['ExSp']={'label': 'Spatial', 'color':'#9575CD'}
ex['ExTe']={'label': 'Temporal', 'color':'#B39DDB'}
existence={'dimension':'Existence','metrics':ex, 'color':'#B39DDB'}

ac={}
ac['AcFo']={'label': 'Format', 'color':'#00838F'}
ac['AcSi']={'label': 'Size', 'color':'#0097A7'}
accuracy={'dimension':'Accurracy', 'metrics':ac, 'color':'#0097A7'}

co={}
co['CoAc']={'label': 'AccessURL', 'color':'#388E3C'}
co['CoCE']={'label': 'ContactEmail', 'color':'#1B5E20'}
co['CoCU']={'label': 'ContactURL', 'color':'#43A047'}
co['CoDa']={'label': 'DateFormat', 'color':'#66BB6A'}
co['CoFo']={'label': 'FileFormat', 'color':'#A5D6A7'}
co['CoLi']={'label': 'License', 'color':'#C8E6C9'}
conformance={'dimension':'Conformance', 'metrics':co, 'color':'#C8E6C9'}

op={}
op['OpFo']={'label': 'Format Openness information', 'color':'#F4511E'}
op['OpLi']={'label': 'License Openneness', 'color':'#FF8A65'}
op['OpMa']={'label': 'Format machine readability', 'color':'#E64A19'}
opendata={'dimension':'Open Data', 'metrics':op, 'color':'#E64A19'}

re={}
re['ReDa']={'label': 'Datasets', 'color':'#FF9800'}
re['ReRe']={'label': 'Resources', 'color':'#FFA726'}
retrievability={'dimension':'Retrievability', 'metrics':re, 'color':'#FFA726'}

qa=[existence, conformance, opendata]#, retrievability, accuracy]




def fetchProcessChart(db, snapshot, n=10):

    snapshots=getLastNSnapshots(snapshot,n)
    nWeeksago=snapshots[-1]

    cnts=defaultdict(int)
    data={}
    for r in db.Session.query(PortalSnapshot.snapshot, PortalSnapshot.start, PortalSnapshot.end-PortalSnapshot.start).filter(PortalSnapshot.snapshot>nWeeksago):
        sn,start, dur = r[0], r[1],r[2]
        cnts[sn]+=1

        d=data.setdefault(sn,{})
        if dur is not None:
            ds=d.setdefault(start,[])
            ds.append(dur.total_seconds())

    for sn, d in data.items():
        dd=[]
        gstart= min(d.keys())

        for start, durations in d.items():
            for dur in durations:
                delta=( start-gstart).total_seconds() + dur
                dd.append(delta)
        data[sn]=dd


    print data

    cnts=defaultdict(int)
    from bokeh.palettes import OrRd9
    bp = figure(plot_width=800, plot_height=400,y_axis_type="datetime",responsive=True,tools='')#,toolbar_location=None
    bp.toolbar.logo = None
    bp.toolbar_location = None


    bp.xaxis[0].formatter = NumeralTickFormatter(format="0.0%")

    def hm(sec):
        m, s = divmod(sec, 60)
        h, m = divmod(m, 60)
        d, h = divmod(h, 24)

        if d==0:
            return "%sh %sm"% (h, m)
        else:
            return "%sd %sh %sm"% (d,h, m)
    bp.yaxis.formatter=FuncTickFormatter.from_py_func(hm)

    bp.xaxis[0].axis_label = '% of portals'
    bp.yaxis[0].axis_label = 'Time elapsed'

    mx=None
    c=0
    for sn in sorted(data.keys()):
        d=data[sn]

        d_sorted = np.sort(np.array(d))
        y=[e for e in d_sorted] #datetime.datetime.fromtimestamp(e)
        x = 1. * arange(len(d)) / (len(d) - 1)
        mx=max(x) if max(x)>mx else mx
        #print x
        # plot the sorted data:
        bp.circle(x,y, size=5, alpha=0.5, legend=str(sn), color=OrRd9[c])
        bp.line(x,y, line_width=2,line_color=OrRd9[c],legend=str(sn))

        c+=1
        #bp.text(,y[-1], line_width=2,line_color=OrRd9[c],legend=str(sn))

        no_olympics_glyph = Text(x=x[-1], y=y[-1], x_offset=100, text=["%s of %s portals"%(len(d),cnts[sn])],
            text_align="right", text_baseline="top",
            text_font_size="9pt", text_font_style="italic", text_color="black")
        bp.add_glyph(no_olympics_glyph)

    bp.set(x_range=Range1d(0, mx*1.2))
    bp.legend.location = "top_left"

    return bp

def qualityChart(df):

    print df

    dim_color = {}
    key_color = {}
    for index, r  in df.iterrows():
        dim_color[r['Dimension']] =r['dim_color']
        key_color[r['Metric']]= r['color']


    width = 800
    height = 800
    inner_radius = 90
    outer_radius = 300 - 10

    minr = 0 #sqrt(log(0 * 1E4))
    maxr = 1#sqrt(log(1 * 1E4))
    a = (outer_radius - inner_radius) / (maxr - minr)
    b = inner_radius

    def rad(mic):
        v = a * mic + b
        return v

    big_angle = 2.0 * np.pi / (len(df) + 1)
    small_angle = big_angle / 7

    x = np.zeros(len(df))
    y = np.zeros(len(df))


    tools = "reset"
    # create chart
    p = figure(plot_width=width, plot_height=height, title="",
        x_axis_type=None, y_axis_type=None,
        x_range=[-420, 420], y_range=[-420, 420],
        min_border=0
        ,responsive=True,tools=''
        #,tools=tools
        #outline_line_color="black",
        #background_fill="#f0e1d2",
        #border_fill="#f0e1d2"
        )
    p.toolbar.logo = None
    p.toolbar_location = None

    p.line(x+1, y+1, alpha=0.5)

    # DIMENSION CIRCLE
    angles = np.pi/2 - big_angle/2 - df.index.to_series()*big_angle
    colors = [dim_color[dim] for dim in df.Dimension]
    p.annular_wedge(
        x, y, outer_radius+15, outer_radius+30, -big_angle+angles, angles, color=colors,
    )

    source = ColumnDataSource(df)
    kcolors = [key_color[k] for k in df.Metric]
    g_r1= p.annular_wedge(x, y, inner_radius, rad(df.value),
        -big_angle+ angles+3*small_angle, -big_angle+angles+6*small_angle,
        color=kcolors, source=source)

    p.annular_wedge(x, y, inner_radius, rad(df.perc),
        -big_angle+ angles+2.5*small_angle, -big_angle+angles+6.5*small_angle, alpha=0.4,
        color='grey')



    g1_hover = HoverTool(renderers=[g_r1],
                         tooltips=[('value', '@value'), ('Metric', '@label'),('Dimension', '@Dimension'),('Percentage', '@perc')])
    p.add_tools(g1_hover)
    #Mrtrics labels
    labels = np.array([c / 100.0 for c in range(0, 110, 10)]) #
    radii = a * labels + b

    p.circle(x, y, radius=radii, fill_color=None, line_color="#d3d3d3")
    p.annular_wedge([0], [0], inner_radius-10, outer_radius+10,
        0.48*np.pi, 0.52 * np.pi, color="white")

    p.text(x, radii, [str(r) for r in labels],
        text_font_size="8pt", text_align="center", text_baseline="middle")

    # radial axes
    p.annular_wedge(x, y, inner_radius, outer_radius+10,
        -big_angle+angles, -big_angle+angles, color="black")


    # Dimension labels
    xr = radii[5]*np.cos(np.array(-big_angle/1.25 + angles))
    yr = radii[5]*np.sin(np.array(-big_angle/1.25 + angles))

    label_angle=np.array(-big_angle/1.4+angles)
    label_angle[label_angle < -np.pi/2] += np.pi # easier to read labels on the left side
    p.text(xr, yr, df.label, angle=label_angle,
        text_font_size="9pt", text_align="center", text_baseline="middle")


    #dim legend
    p.rect([-40,-40, -40, -40,-40], [36,18, 0, -18, -36], width=30, height=13,
        color=list(dim_color.values()))
    p.text([-15,-15, -15, -15,-15], [36,18, 0, -18,-36], text=list(dim_color.keys()),
        text_font_size="9pt", text_align="left", text_baseline="middle")

    #p.logo = None
    #p.toolbar_location = None

    return p