'''
Created on Aug 12, 2015

@author: jumbrich
'''
from odpw.analysers import Analyser
from _collections import defaultdict
from odpw.analysers.datasetlife import DatasetLifeStatsAnalyser
from odpw.analysers.core import DBAnalyser
from odpw.utils.util import tofirstdayinisoweek


class SystemEvolutionAnalyser(DBAnalyser):
    pass


class EvolutionCountAnalyser(Analyser):
    
    def __init__(self):
        self._evolv={}
        self.keys=set([])
        
    def add(self, snapshot, key, value):
        sndict = self._evolv.get(snapshot, defaultdict(int))
        if value is None:
            value=-1
        sndict[key]+=value
        self._evolv[snapshot]=sndict
        self.keys.add(key)

    def getResult(self):
        res={}
        for sn, ddict in self._evolv.items():
            res[sn]= { k: ddict.get(k) for k in self.keys}
        return res

class EvolutionAggregator(Analyser):

    def __init__(self):
        super(EvolutionAggregator, self).__init__()
        self.results={}

    def analyse_EvolutionCountAnalyser(self, a):
        for sn,v in a.getResult().items():
            fd=str(tofirstdayinisoweek(sn).date())
            d= self.results.setdefault(fd,{})
            d.setdefault('sn',sn)
            de= d.setdefault('values',{})
            de.update(v)

    def getResult(self):
        return {'evolution':self.results}


class DatasetEvolution(EvolutionCountAnalyser):
    def __init__(self):
        super(DatasetEvolution, self).__init__()
    
    def analyse_PortalMetaData(self, pmd):
        if pmd.datasets is not None:
            self.add(pmd.snapshot, 'datasets', pmd.datasets)

    
class ResourceEvolution(EvolutionCountAnalyser):
    def __init__(self):
        super(ResourceEvolution, self).__init__()
    def analyse_PortalMetaData(self, pmd):
        if pmd.resources is not None:
            self.add(pmd.snapshot, 'resources', pmd.resources)
        
        #self.add(pmd.snapshot, 'resources',pmd.resources)

class QualityEvolution(EvolutionCountAnalyser):
    def __init__(self):
        super(QualityEvolution, self).__init__()
    def analyse_PortalMetaData(self, pmd):
        if pmd.qa_stats:
            for k,v in pmd.qa_stats.items():
                if '_hist' not in k:
                    self.add(pmd.snapshot, k, v['value'])


class ResourceAnalysedEvolution(EvolutionCountAnalyser):
    def analyse_PortalMetaData(self, pmd):
        count=0
        if pmd.res_stats and 'status' in pmd.res_stats:
            count = sum(pmd.res_stats['status'].values())
        self.add(pmd.snapshot, 'resources_analysed',count)

        
class SystemSoftwareEvolution(EvolutionCountAnalyser):
    
    def __init__(self, portalSoftware):
        self.portalSoftware= portalSoftware
        super(SystemSoftwareEvolution, self).__init__()
        
    def analyse_PortalMetaData(self, pmd):
        self.add(pmd.snapshot, self.portalSoftware[pmd.portal_id], 1)



class DatasetDCATMetricsEvolution(EvolutionCountAnalyser):
    def __init__(self, metrics):
        super(DatasetDCATMetricsEvolution, self).__init__()
        self.metrics = metrics
    
    def name(self):
        return 'DatasetDCATMetricsEvolution'+('_'.join(self.metrics))
        

    def analyse_PortalMetaData(self, pmd):
        if pmd.qa_stats:
            print self.metrics
            #if 'OpFo' in self.metrics:
            print pmd.qa_stats    
            for m in self.metrics:
                self.add(pmd.snapshot, m, pmd.qa_stats.get(m, 0))
        else:
            self.add(pmd.snapshot, 'no_qa_stats', 1)

class PMDCountEvolution(EvolutionCountAnalyser):
    def analyse_PortalMetaData(self, pmd):
        if pmd.datasets:
            self.add(pmd.snapshot, 'datasets', pmd.datasets)
        else:
            self.add(pmd.snapshot,'no_datasets', 1)

        if pmd.resources:
            self.add(pmd.snapshot, 'resources', pmd.resources)
        else:
            self.add(pmd.snapshot,'no_resources', 1)