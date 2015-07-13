from odpw.db.models import Portal
import pandas
from odpw.timer import Timer
from odpw.util import timer
import types


__author__ = 'jumbrich'

from _collections import defaultdict
import time

class Analyser:
    def analyse(self, element): pass
    def getResult(self): pass
    def getDataFrame(self): pass
    @classmethod
    def name(cls): return cls.__name__
    def done(self): pass


    
class DistributionAnalser():
    def __init__(self):
        self.dist=defaultdict(int)
    def add(self, value): 
        self.dist[value]+=1
    def getDist(self):
        return dict(self.dist)
    

class StatusCodeDistribution():
    dist={
                '2':'ok',
                '3':'redirect-loop',
                '4':'offline',
                '5':'server-error',
                '6':'other-error',
                '7':'connection-error',
                '8':'value-error',
                '9':'uri-error',
                '-':'unknown',
                'total':'total'
    }

    def __init__(self):
        self.dist=defaultdict(int)
    def add(self, value):
        status = sstr=str(value)[0]
        self.dist[status]+=1
        self.dist['total']+=1

    def getDist(self):
        d={}
        for k,v in dict(self.dist).iteritems():
            d[k]={'count':v, 'label': self.__class__.dist[k]}
        return d
    
    
    
    
class PortalSoftwareDistAnalyser(Analyser,DistributionAnalser):
    def analyse(self, portal):
        if not isinstance(portal, Portal):
            pass
        self.add(portal.software)
    def getResult(self):
        return self.getDist()
    def getDataFrame(self):
        return pandas.DataFrame([[col1,col2] for col1,col2 in self.getDist().items()], columns=['software', 'count'])

class PortalCountryDistAnalyser(Analyser,DistributionAnalser):
    def analyse(self, portal):
        if not isinstance(portal, Portal):
            pass
        self.add(portal.country)
    def getResult(self):
        return self.getDist()
    def getDataFrame(self):
        return pandas.DataFrame([[col1,col2] for col1,col2 in self.getDist().items()], columns=['country', 'count'])
        

class PortalStatusAnalyser(StatusCodeDistribution, Analyser):
    def analyse(self, portal):
        if not isinstance(portal, Portal):
            pass
        self.add(portal.status)
        
    def getResult(self):
        return self.getDist()

    def getDataFrame(self):
        return pandas.DataFrame([[status,val['count'],val['label']] for status, val in self.getDist().items() ], columns=['status_prefix', 'count', 'label'])


class AnalyseEngine:
    def __init__(self):
        self.analysers = {}
        
    def add(self, analyser):
        self.analysers[analyser.name()] = analyser

    def analyse(self, element):
        with Timer(key="analyse") as t:
            for c in self.analysers.itervalues():
                c.analyse(element)
    
    def done(self):
        for c in self.analysers.itervalues():
            c.done()
        self.end=time.time()
        print 'AnalyseEngine elapsed time: %s (%f ms)' % (timer(self.end-self.start),(self.end-self.start)*1000)
    
    def process_all(self, iterable):
        self.start= time.time()
        for c in iterable:
            self.analyse(c)
        self.done()
            
    def getAnalyser(self, analyser):
        
        if isinstance(analyser, (types.TypeType, types.ClassType)) and  issubclass(analyser, Analyser):
            return self.analysers[analyser.name()]
        elif isinstance(analyser, analyser):
            return self.analysers[analyser.name()]