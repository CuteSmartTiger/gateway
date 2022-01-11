import json
import requests
import urllib3
from logger import logger
import traceback
urllib3.disable_warnings()


class KongDumper:
    def __init__(self, namespace,kongAddr) -> None:
        self.kongAddr = kongAddr.rstrip('/')
        self.namespace = namespace
        self.s = requests.Session()
        self.namespaceTmpl = r'{{   NAMESPACE  }}'

    def getAllData(self, resource):
        logger.info("Getting resource: %s " % (resource))
        if not resource.startswith('/'):
            resource = '/' + resource
        allData = []
        pageIndex = 1
        while True:
            r = self.s.get(self.kongAddr+resource, verify=False).json()
            logger.info('Page: %s, Size: %s' %
                        (pageIndex, r['data'].__len__()))
            pageIndex += 1
            if r['next'] == None:
                allData = allData + r['data']
                break
            else:
                resource = r['next']
                allData = allData + r['data']
                continue
        logger.info("Service sum: %s " % (allData.__len__()))
        return(allData)

    def serviceDumper(self):
        allSvc = self.getAllData(resource='services')
        filterResult = []
        for svc in allSvc:
            try:
                serviceNs = svc['name'].rsplit('.')[1]
            except IndexError:
                logger.error('Index error : %s', svc)
                continue
            if serviceNs == self.namespace:
                filterResult.append(svc)
        logger.info('Filter namespace: %s ,resource: [SERVICE],count: %s' %
                    (self.namespace, filterResult.__len__()))
        for svc in filterResult:
            # popList = ['id','updated_at', 'created_at']
            popList = ['updated_at', 'created_at']

            for popItem in popList:
                try:
                    svc.pop(popItem)
                except KeyError:
                    pass

            plugins = self.s.get(url='%s/services/%s/plugins'% (self.kongAddr,svc['name'])).json()['data']
            if plugins == []:
                pass
            else:
                pluginList=[]
                for plugin in plugins:
                    for popItem in popList:
                        try:
                            plugin.pop(popItem)
                        except KeyError:
                            pass
                    plugin['service']['name'] = '%s.%s' % (svc['name'].rsplit('.')[0],self.namespaceTmpl)
                    plugin['service'].pop('id')
                    plugin.pop('protocols')
                    if 'anonymous' in plugin['config']:
                        if plugin['config']['anonymous'] is not None:
                            plugin['config']['anonymous']=r'{{ KONG_ANONYMOUS }}'
                        
                    if 'config' in plugin:
                        if plugin['config'] is not None:
                            if 'namespace' in plugin['config']:
                                if plugin['config']['namespace'] is not None:
                                    plugin['config']['namespace']=self.namespaceTmpl
                    pluginList.append(plugin)

            svc['host'] = svc['host'].replace(
                self.namespace, self.namespaceTmpl)
            svc['name'] = svc['name'].replace(
                self.namespace, self.namespaceTmpl)
                
            dstFile = open('./kong_configs/tmpl/service/%s.json' %
                           svc['name'].split('.')[0], mode='wt')
            dstFile.write(json.dumps(svc, indent=4, ensure_ascii=False))
            logger.info('Writing service: [%s] templates.' % (svc['name'].rsplit('.')[0]))
            dstFile.close()
            
            if plugins == []:
                pass
            else:
                pluginFile = open('./kong_configs/tmpl/plugin/%s.json' %
                            svc['name'].split('.')[0], mode='wt')
                pluginFile.write(json.dumps(pluginList, indent=4, ensure_ascii=False))
                logger.info('Writing service: [%s] plugin templates.' % (svc['name'].rsplit('.')[0]))
                pluginFile.close()

    def routeDumper(self):
        allRot = self.getAllData(resource='routes')
        filterResult = []
        for rot in allRot:
            try:
                rotNs = rot['name'].rsplit('.')[1]
            except IndexError:
                logger.error('Index error : %s', rot)
                continue
            if rotNs == self.namespace:
                filterResult.append(rot)
        logger.info('Filter namespace: %s ,resource: [ROUTE],count: %s' %
                    (self.namespace, filterResult.__len__()))
        for rot in filterResult:
            popList = ['id', 'updated_at', 'created_at']
            for popItem in popList:
                rot.pop(popItem)

            routes = self.s.get(url='%s/routes/%s/plugins'% (self.kongAddr,rot['name'])).json()['data']
            if routes == []:
                pass
            else:
                pluginList=[]
                for plugin in routes:
                    for popItem in popList:
                        try:
                            plugin.pop(popItem)
                        except KeyError:
                            pass
                    plugin['route']['name'] = '%s.%s' % (rot['name'].rsplit('.')[0],self.namespaceTmpl)
                    plugin['route'].pop('id')
                    plugin.pop('protocols')
                    if 'anonymous' in plugin['config']:
                        if plugin['config']['anonymous'] is not None:
                            plugin['config']['anonymous'] = r'{{ KONG_ANONYMOUS }}'
                    pluginList.append(plugin)

            rotName = self.s.get(url='%s/services/%s' % (self.kongAddr, rot['service']['id'])).json()['name']
            rot['service'] = {'name': rotName.replace(self.namespace, self.namespaceTmpl)}
            rot['name'] = rot['name'].replace(self.namespace, self.namespaceTmpl)

            hostsTmpl = '''"hosts": 
            {%- if DOMAIN -%}
            [{%- if OP_DOMAIN -%}"{{    OP_DOMAIN    }}",{% endif %}
            "{{    DOMAIN    }}"
            ]{% else %}null
            {% endif %}'''
            rot['hosts'] = []

            destFileName = rot['name'].split('.')[0]
            if 'httpbin' in destFileName:
                rot['paths'][0] = rot['paths'][0].replace(
                    self.namespace, self.namespaceTmpl)
                rot['hosts'] = None
            else:
                unDomainPathList = []
                DomainPathList = []
                for path in rot['paths']:
                    try:
                        if path.split('/', 2)[1] == self.namespace:
                            unDomainPathList.append(
                                '/%s/%s' % (self.namespaceTmpl, path.split('/', 2)[2]))
                            if path.split('/', 3)[3] in ['hawkeye','mqtt/ws']:
                                DomainPathList.append('/%s' % path.split('/', 3)[3])
                            else:
                                DomainPathList.append('/console/%s' % path.split('/', 3)[3])
                        else:
                            DomainPathList.append(path)
                            if path.split('/',1)[1].startswith('console'):
                                unDomainPathList.append('/%s/latest/%s' % (self.namespaceTmpl,path.split('/',1)[1].split('/')[1]))
                            else:
                                unDomainPathList.append('/%s/latest/%s' % (self.namespaceTmpl,path.split('/',1)[1]))
                    except IndexError:
                        logger.error('Index error: %s', path)
                        continue
                domainPath=''
                for path in DomainPathList:
                    domainPath='%s"%s",\n' % (domainPath,path)

                undomainPath=''
                for path in unDomainPathList:
                    undomainPath='%s"%s",\n' % (undomainPath,path)
                
                pathsTmpl1='"paths": [\n{%- if DOMAIN -%}'
                pathsTmpl2='{% else %}'
                pathsTmpl3='{% endif %}\n]'

                pathsTmpl=('{}\n{}\n{}\n{}\n{}').format(pathsTmpl1,domainPath.strip(',\n'),pathsTmpl2,undomainPath.strip(',\n'),pathsTmpl3)
                rot['paths'] = []

            dstFile = open('./kong_configs/tmpl/route/%s.json' %
                            destFileName, mode='wt')
            dstFile.write(json.dumps(rot, indent=4, ensure_ascii=True))
            dstFile.close()

            dstFile = open('./kong_configs/tmpl/route/%s.json' %
                            destFileName, mode='rt')
            dstFileStr = dstFile.read()
            dstFile.close()

            dstFileStr = dstFileStr.replace(r'"hosts": []', hostsTmpl)
            dstFileStr = dstFileStr.replace(r'"paths": []', pathsTmpl)

            dstFile = open('./kong_configs/tmpl/route/%s.json' %
                            destFileName, mode='wt')
            dstFile.write(dstFileStr)
            logger.info('Writing route: [%s] templates.' % (rot['name'].rsplit('.')[0]))
            dstFile.close()

            if routes == []:
                pass
            else:
                pluginFile = open('./kong_configs/tmpl/plugin/%s.json' %
                            rot['name'].split('.')[0], mode='wt')
                pluginFile.write(json.dumps(pluginList, indent=4, ensure_ascii=False))
                logger.info('Writing route: [%s] plugin templates.' % (rot['name'].rsplit('.')[0]))
                pluginFile.close()

    def consumer(self):
        allData = self.getAllData(resource='consumers')
        filterResult = []
        for data in allData:
            try:
                namespace = data['username'].rsplit('.')[-1]
            except Exception as e:
                logger.error('Error : %s', traceback.format_exc() )
                continue
            if namespace == self.namespace:
                filterResult.append(data)

        logger.info('Filter namespace: %s ,consumers: [CONSUMERS],count: %s' %
                    (self.namespace, filterResult.__len__()))

        popList = ['id', 'created_at']
        for consumer in filterResult:
            for popItem in popList:
                consumer.pop(popItem)

        # todo consumers  plugins
        if filterResult:
            with open('./kong_configs/tmpl/consumers/%s.json' % self.namespace, mode='wt') as dstFile:
                dstFile.write(json.dumps(filterResult, indent=4, ensure_ascii=False))
                logger.info('Writing consumers: [%s] templates.' % self.namespace)


if __name__ == '__main__':
    try:
        # kongAddr= input('Source Kong Admin url [e.g: http(s)://kong.uisee.com:30001/]: ')
        # namespace= input('namespace: ')
        kongAddr = "https://10.0.162.5:31860"
        # kongAddr = "https://10.0.169.20:31102"
        # namespace = "dongwu-simulation"
        namespace = "nh3gowg"
        print('\nPlease confirm your config:\nKong address: %s\nnamespace: %s\n' %(kongAddr,namespace))
        while True:
            # confirm = input('Confirm: [N/y]: ')
            confirm = 'y'
            if confirm.strip(' ') == 'y':
                kongdumper = KongDumper(kongAddr=kongAddr,namespace=namespace)
                # kongdumper.serviceDumper()
                # kongdumper.routeDumper()
                kongdumper.consumer()
                logger.info('Kong dump finished.')
                break
            elif confirm.strip(' ') == "":
                continue
            else:
                print('Bye.')
                break
    except KeyboardInterrupt:
        print('\n"Ctrl+c" catched, Bye.')