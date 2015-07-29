from ast import literal_eval
import random
import urlparse
import ckanapi
import time
from odpw.utils import util
from odpw.db import models
from odpw.db.models import Dataset
import requests
from odpw.utils.timer import Timer
from odpw.utils.util import ErrorHandler as eh, progressIndicator

from odpw.analysers import AnalyseEngine

import logging
logger = logging.getLogger(__name__)
from structlog import get_logger, configure
from structlog.stdlib import LoggerFactory
configure(logger_factory=LoggerFactory())
log = get_logger()


class PortalProcessor:
    """
    abstract super class for different portal software (e.g., Socrata, CKAN)
    """

    def __init__(self, analyse_engine):
        self.analyse_engine = analyse_engine

    def generateFetchDatasetIter(self, Portal, sn):
        raise NotImplementedError("Should have implemented this")

    def fetching(self, Portal, sn):
        Portal.latest_snapshot=sn

        iter = self.generateFetchDatasetIter(Portal, sn)
        self.analyse_engine.process_all(iter)



class CKAN(PortalProcessor):
    def _waiting_time(self, attempt):
        if attempt == 1:
            return 3
        else:
            return attempt*attempt*5

    def generateFetchDatasetIter(self, Portal, sn, timeout_attempts=5):
        api = ckanapi.RemoteCKAN(Portal.apiurl, get_only=True)
        start=0
        rows=1000000

        p_count=0
        p_steps=1
        total=0
        processed=set([])
        try:

            response = api.action.package_search(rows=0)
            total = response["count"]
            p_steps=total/10
            if p_steps ==0:
                p_steps=1
            while True:

                for attempt in xrange(timeout_attempts):
                    time.sleep(self._waiting_time(attempt))
                    try:
                        response = api.action.package_search(rows=rows, start=start)
                        break
                    except ckanapi.errors.CKANAPIError as e:
                        err = literal_eval(e.extra_msg)
                        if 500 <= err[1] < 600:
                            log.warn("CKANPackageSearchFetch", pid=Portal.id, error='Internal Server Error. Retrying after waiting time.', errorCode=str(err[1]), attempt=attempt)
                        else:
                            raise e
                    print 'SHOULD NOT HAPPEN'

                #print Portal.apiurl, start, rows, len(processed)
                datasets = response["results"] if response else None
                if datasets:
                    rows = len(datasets) if start==0 else rows
                    start+=rows
                    for datasetJSON in datasets:
                        datasetID = datasetJSON['name']

                        if datasetID not in processed:
                            data = datasetJSON

                            d = Dataset(snapshot=sn,portal=Portal.id, dataset=datasetID, data=data)
                            d.status=200

                            processed.add(datasetID)

                            if len(processed) % 1000 == 0:
                                log.info("ProgressDSFetch", pid=Portal.id, processed=len(processed))

                            p_count+=1
                            if p_count%p_steps ==0:
                                progressIndicator(p_count, total, label=Portal.id)
                            yield d

                else:
                    break
            progressIndicator(p_count, total, label=Portal.id)
            #if len(processed) == total:
            #    #assuming that package_search['count']
            #    return
        except Exception as e:
            pass



        try:
            package_list, status = util.getPackageList(Portal.apiurl)
            if total >0 and len(package_list) !=total:
                log.info("PackageList_COUNT", total=total, pid=Portal.id, pl=len(package_list))
            #len(package_list)

            for entity in package_list:
                #WAIT between two consecutive GET requests
                if entity not in processed:

                    time.sleep(random.uniform(0.5, 1))
                    log.debug("GETMetaData", pid=Portal.id, did=entity)
                    with Timer(key="fetchDS("+Portal.id+")") as t, Timer(key="fetchDS") as t1:
                        #fetchDataset(entity, stats, dbm, sn)
                        props={
                               'status':-1,
                               'data':None,
                               'exception':None
                               }
                        try:
                            resp = util.getPackage(api=api, apiurl=Portal.apiurl, id=entity)
                            data = resp
                            util.extras_to_dict(data)
                            props['data']=data
                            props['status']=200
                        except Exception as e:
                            eh.handleError(log,'FetchDataset', exception=e,pid=Portal.id, did=entity,
                               exc_info=True)
                            props['status']=util.getExceptionCode(e)
                            props['exception']=util.getExceptionString(e)

                        d = Dataset(snapshot=sn,portal=Portal.id, dataset=entity, **props)
                        processed.add(d.dataset)

                        if len(processed) % 1000 == 0:
                            log.info("ProgressDSFetch", pid=Portal.id, processed=len(processed))

                        yield d

        except Exception as e:
            if len(processed)==0:
                raise e


class Socrata(PortalProcessor):
    def generateFetchDatasetIter(self, Portal, sn, dcat=False):

        api = urlparse.urljoin(Portal.url, '/api/')
        page = 1
        processed=set([])

        while True:
            resp = requests.get(urlparse.urljoin(api, '/views?page=' + str(page)), verify=False)
            if resp.status_code != requests.codes.ok:
                # TODO wait? appropriate message
                pass

            res = resp.json()
            # returns a list of datasets
            if not res:
                break
            for datasetJSON in res:
                datasetID = datasetJSON['id']
                if datasetID not in processed:
                    processed.add(datasetID)
                    d = Dataset(snapshot=sn, portal=Portal.id, dataset=datasetID, data=datasetJSON)
                    d.status = 200
                    if dcat:
                        try:
                            dcat_data = self._dcat(datasetID, api)
                        except Exception as e:
                            dcat_data = None
                        d.dcat = dcat_data

                    if len(processed) % 1000 == 0:
                        log.info("ProgressDSFetch", pid=Portal.id, processed=len(processed))
                    yield d
            page += 1

    def _dcat(self, id, api):
        url = urlparse.urljoin(api, 'dcat.json/' + id)
        resp = requests.get(url, verify=False)
        if resp.status_code == 200:
            # returns a list of datasets
            res = resp.json()
            return res
        return None



class OpenDataSoft(PortalProcessor):
    def generateFetchDatasetIter(self, Portal, sn):
        start=0
        rows=1000000
        processed=set([])

        while True:
            query = '/api/datasets/1.0/search?rows=' + str(rows) + '&start=' + str(start)
            resp = requests.get(urlparse.urljoin(Portal.url, query), verify=False)
            res = resp.json()
            datasets = res['datasets']
            if datasets:
                rows = len(datasets) if start==0 else rows
                start+=rows
                for datasetJSON in datasets:
                    datasetID = datasetJSON['datasetid']

                    if datasetID not in processed:
                        data = datasetJSON
                        d = Dataset(snapshot=sn,portal=Portal.id, dataset=datasetID, data=data)
                        d.status=200
                        processed.add(datasetID)

                        if len(processed) % 1000 == 0:
                            log.info("ProgressDSFetch", pid=Portal.id, processed=len(processed))
                        yield d
            else:
                break


if __name__ == '__main__':
    # TESTING
    ae = AnalyseEngine()
    # TODO all analysers

    p = CKAN(analyse_engine=ae)
    p.fetching(models.Portal('http://datahub.io/', 'http://datahub.io/'), '1')

    for a in ae.getAnalysers():
        #updatePMDwithAnalyserResults(pmd, ae)
        #pmd.update(ae)
        pass
