#!/usr/bin/env python
# -*- coding: utf-8 -*-

from tornado.web import RequestHandler, HTTPError, asynchronous
from jinja2.exceptions import TemplateNotFound
from tornado.escape import json_encode

from odpw.db.models import Portal, PortalMetaData, Dataset
from odpw.utils  import util
from collections import defaultdict
from urlparse import urlparse 
import json
from odpw.db.dbm import nested_json, date_handler
from odpw.reporting.reporters import DBAnalyser, DFtoListDict, addPercentageCol,\
    Report, ISO3DistReporter, SoftWareDistReporter,\
    SystemActivityReporter, SnapshotsPerPortalReporter, LicensesReporter,\
    TagReporter, OrganisationReporter, FormatCountReporter, DatasetSumReporter,\
    ResourceSumReporter, ResourceSizeReporter, ResourceCountReporter, DBReporter
from odpw.utils.timer import Timer
from odpw.analysers import process_all, AnalyserSet

import sys
import traceback
import os
from odpw.analysers.pmd_analysers import PMDActivityAnalyser
from odpw.analysers.fetching import  CKANLicenseConformance
    

from odpw.analysers.count_analysers import DCATTagsCount, DCATOrganizationsCount,\
    DCATFormatCount, DatasetCount, ResourceCount, PMDResourceStatsCount
from odpw.analysers.core import DCATConverter
from odpw.analysers.resource_analysers import ResourceSize
from odpw.reporting.activity_reports import systemactivity
from odpw.reporting.evolution_reports import portalevolution
from odpw.reporting.info_reports import portalinfo, SystemPortalInfoReporter
from odpw.reporting.quality_reports import portalquality




class BaseHandler(RequestHandler):
    @property
    def env(self):
        return self.application.env

    @property
    def db(self):
        return self.application.db
    @property
    def printHtml(self):
        return self.application.printHtml

    def get_error_html(self, status_code, **kwargs):
        print "error", status_code, kwargs
        try:
            self.render('error/{}.html'.format(status_code))
        except (TemplateNotFound, HTTPError):
            try:
                self.render('error/50x.html', status_code=status_code)
            except (TemplateNotFound, HTTPError):
                self.write("You aren't supposed to see this")

    def render(self, templateName, **kwargs):
        try:
            template = self.env.get_template(templateName)
        except TemplateNotFound:
            raise HTTPError(404)
        self.env.globals['static_url'] = self.static_url
        if self.printHtml:
            try:
                import codecs
                file=os.path.join(os.path.dirname(self.printHtml) ,templateName+'.html')
                with codecs.open(file, 'wb', 'utf-8') as f:
                    print "write render file to ",file
                    f.write(template.render( kwargs ))
                    print "done"
            except TemplateNotFound as e:
                print e
        
        self.write(template.render(kwargs))
        
    def _handle_request_exception(self, e):
        print e
        traceback.print_exc(file=sys.stdout)


class NoDestinationHandler(RequestHandler):
    def get(self):
        raise HTTPError(503)

class PortalSelectionHandler(BaseHandler):
    
    def get(self, **params):
        a= process_all( DBAnalyser(), self.db.getSnapshots( portalID=None,apiurl=None))
        rep = Report([SnapshotsPerPortalReporter(a,None)])
        self.render('portal_empty.jinja',portals=True, data=rep.uireport())
    
class PortalHandler(BaseHandler):
    def get(self, view=None, portalID=None, snapshot=None):
        
        
        portals= {}
        for P in Portal.iter(self.db.getPortals()):
            portals[P.id]={"url":P.url, "software":P.software, "iso3":P.iso3}
        
        if not portalID:
            print 'portal emtpy'
            a= process_all( DBAnalyser(), self.db.getSnapshotsFromPMD(portalID=None))
            rep = SnapshotsPerPortalReporter(a, None)
        
            self.render('portal_empty.jinja', portal=True, data=rep.uireport(),portals=portals)
        
        if portalID:
            if len(portalID.split(",")) ==1:
                #Portal = self.db.getPortal(portalID=portalID)
                
                fun= getattr(self, view+"rendering")
                fun(portalID, snapshot,portals)
            else:
                self.render('portals_detail.jinja', portal=True)
            
    
    def inforendering(self, portalID, snapshot, portals):      
        with Timer(key="viewrendering", verbose=True) as t:
            r = portalinfo(self.db, snapshot, portalID)
            self.render('portal_info.jinja', portal=True, data=r.uireport(), portalID=portalID, snapshot=snapshot,portals=portals)
    
    def evolutionrendering(self, portalID, snapshot,portals):      
        with Timer(key="evolutionrendering", verbose=True) as t:
            a= process_all( DBAnalyser(), self.db.getSnapshotsFromPMD( portalID=None))
            rep = SnapshotsPerPortalReporter(a,None)
        
            r = portalevolution(self.db, snapshot, portalID)
            rep = Report([rep,r])
            self.render('portal_evolution.jinja', portal=True, data=rep.uireport(), portalID=portalID, snapshot=snapshot)
        
    def qualityrendering(self, portalID, snapshot,portals):
        with Timer(key="qualityrendering", verbose=True) as t:
            a= process_all( DBAnalyser(), self.db.getSnapshotsFromPMD( portalID=None))
            rep = SnapshotsPerPortalReporter(a,None)
        
            r = portalquality(self.db, snapshot, portalID)
            rep = Report([rep,r])
            self.render('portal_quality.jinja', portal=True, data=rep.uireport(), portalID=portalID, snapshot=snapshot,portals=portals)
        
        
        
class PortalList(BaseHandler):
    def get(self):
        with Timer(verbose=True) as t:
            try:
                p={}
                print "getting portals"
                for por in self.db.getPortals():
                    p[por['id']]={'iso3':por['iso3'],'software':por['software']}
                portals=[]
                print "getting latest meta data" 
                for pRes in self.db.getLatestPortalMetaDatas():
                    rdict= dict(pRes)
                    if rdict['portal_id'] in p:
                        rdict['iso3']=p[rdict['portal_id']]['iso3']
                        rdict['software']=p[rdict['portal_id']]['software'] 
            
                    portals.append(rdict)
        
                self.render('portallist.jinja',index=True, data=portals)
            except Exception as e:print e

class IndexHandler(BaseHandler):
    def get(self):
            a = process_all(DBAnalyser(),self.db.getSystemPortalInfo())
            r = SystemPortalInfoReporter(a)
                        
            r = Report([r])
            args={
                  'index':True,
                  'data':r.uireport(),
            }    
            self.render('index.jinja',**args)
        
class SystemActivityHandler(BaseHandler):
    def get(self, snapshot=None):
        with Timer(key='SystemActivityHandler', verbose=True) as t:
            if not snapshot:
                sn = util.getCurrentSnapshot()
            else:
                sn = snapshot
            
            report = systemactivity(self.db, sn)
            
            args={'index':True,
               'data':report.uireport(),
               'snapshot':sn
            }    
            self.render('system_activity.jinja',**args)
        
        
class DataHandler(RequestHandler):
    @property
    def db(self):
        return self.application.db
    
    def get(self, source):
        print source
        if source == 'datasets':
            d=['portalID','limit','snapshot','software','status','statuspre']
            props={}
            for k in d:
                props[k]=self.get_argument(k, None)
            
            res=[]
            print props
            for d in Dataset.iter(self.db.getDatasets(**props)):
                res.append({'id':d.id,'status':d.status,'portalID':d.portal_id})
            
            
            self.set_header('Content-Type', 'application/json')
            self.write(json_encode(res))