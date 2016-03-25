'''
Created on Aug 18, 2015

@author: jumbrich
'''
from collections import Counter
import csv
import json
from odpw.analysers import Analyser
from odpw.analysers.core import ElementCountAnalyser

from odpw.analysers.quality.analysers import ODM_formats
from odpw.utils.dcat_access import getDistributionFormats, getDistributionMediaTypes

OPEN_FORMATS = ['dvi', 'svg'] + ODM_formats.get_non_proprietary()
MACHINE_FORMATS = ODM_formats.get_machine_readable()



class ContainsFormatDCATAnalyser(Analyser):

    def __init__(self, contains_set):
        super(ContainsFormatDCATAnalyser, self).__init__()
        self.quality = None
        self.values = []
        self.total = 0
        self.contains_set = contains_set


    def analyse_Dataset(self, dataset):
        formats = getDistributionFormats(dataset)
        # resource level
        t = 0.0
        c = 0.0
        for v in formats:
            t += 1
            v = v.encode('utf-8').strip()
            v = v.lower()
            if v.startswith('.'):
                v = v[1:]

            if v in self.contains_set:
                c += 1

        if len(formats) > 0:
            self.total += 1
        v = c/t if t > 0 else 0

        self.values.append(v)
        return v

    def getResult(self):
        return {'value': self.quality, 'total':self.total, 'hist':self.hist()}

    def hist(self):
        cnt = Counter(self.values)
        return dict(cnt)

    def analyse_ContainsFormatDCATAnalyser(self,analyser):
        self.values=self.values+analyser.values
        self.total+=analyser.total

    def done(self):
        self.quality = sum(self.values)/self.total if self.total > 0 else 0


class FormatOpennessDCATAnalyser(ContainsFormatDCATAnalyser):

    def __init__(self):
        super(FormatOpennessDCATAnalyser, self).__init__(OPEN_FORMATS)
        self.id = 'OpFo'



    def update_PortalMetaData(self, pmd):
        if not pmd.qa_stats:
            pmd.qa_stats = {}
        pmd.qa_stats[self.id] = self.getResult()
        cnt = Counter(self.values)


class FormatMachineReadableDCATAnalyser(ContainsFormatDCATAnalyser):
    def __init__(self):
        super(FormatMachineReadableDCATAnalyser, self).__init__(MACHINE_FORMATS)
        self.id = 'OpMa'



    def update_PortalMetaData(self, pmd):
        if not pmd.qa_stats:
            pmd.qa_stats = {}
        pmd.qa_stats[self.id] = self.getResult()



class IANAFormatDCATAnalyser(Analyser):
    def __init__(self):
        super(IANAFormatDCATAnalyser, self).__init__()
        self.id = 'CoFo'

        self.quality = None
        self.values = []
        self.total = 0
        self.names = set()
        self.endings = set()
        self.mimetypes = set()
        from pkg_resources import  resource_filename
        for p in ['application.csv', 'audio.csv', 'image.csv', 'message.csv', 'model.csv', 'multipart.csv', 'text.csv',
                  'video.csv']:
            with open(resource_filename('odpw.resources.iana', p)) as f:
                reader = csv.reader(f)
                # skip header
                reader.next()
                for row in reader:
                    self.names.add(row[0].strip().lower())
                    self.mimetypes.add(row[1].strip().lower())
        with open(resource_filename('odpw.resources.iana','mimetypes.json')) as f:
            mappings = json.load(f)
            for dict in mappings:
                for k in dict:
                    if dict[k] in self.mimetypes:
                        self.endings.add(k[1:])

    def analyse_Dataset(self, dataset):
        formats = []
        formats += getDistributionFormats(dataset)
        formats += getDistributionMediaTypes(dataset)
        if len(formats) == 0:
            self.analyse_generic('no values')

        # resource level
        t = 0.0
        c = 0.0
        for v in formats:
            t += 1
            v = v.encode('utf-8').strip()
            v = v.lower()
            if v.startswith('.'):
                v = v[1:]

            if self.is_in_iana(v):
                c += 1

        if len(formats) > 0:
            self.total += 1
        v = c/t if t > 0 else 0

        self.values.append(v)

        return v

    def analyse_IANAFormatDCATAnalyser(self, analyser):
        self.values=self.values+analyser.values
        self.total+=analyser.total


    def is_in_iana(self, v):
        return v in self.names or v in self.mimetypes or v in self.endings

    def getResult(self):
        return {'value': self.quality, 'total':self.total, 'hist':self.hist()}

    def hist(self):
        cnt = Counter(self.values)
        return dict(cnt)

    def done(self):
        self.quality = sum(self.values)/self.total if self.total > 0 else 0

    def update_PortalMetaData(self, pmd):
        if not pmd.qa_stats:
            pmd.qa_stats = {}
        pmd.qa_stats[self.id] = self.getResult()

