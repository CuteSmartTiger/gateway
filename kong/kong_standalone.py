from posix import listdir
import requests
import json
from logger import logger

from jinja2 import Environment, FileSystemLoader
import os
import requests
from ruamel import yaml

import json
import requests
import urllib3
urllib3.disable_warnings()

                
def render_template(template, value_file, output=None):

    valuefile = open(value_file, 'rt')
    value = valuefile.read()
    yfile = yaml.safe_load(value)

    basepath = os.path.dirname(template)
    filename = os.path.basename(template)

    templateLoader = FileSystemLoader(searchpath=basepath)
    env = Environment(loader=templateLoader)
    tmpl = env.get_template(filename)
    result = tmpl.render(yfile)
    with open(output, "w") as fh:
        fh.write(result)


class KongaImporter:
    def __init__(self, clusterKong,namespace,domain=None,op_domain=None) -> None:
        super().__init__()
        self.clusterKong = clusterKong.rstrip('/')
        self.namespace = namespace
        self.domain = domain
        self.op_domain = op_domain
        self.session = requests.session()
        self.value_file = './kong_configs/value.yaml'
        self.baseDir = './kong_configs/'
        print(self.clusterKong)
        consumerUrl = self.clusterKong + '/consumers/anonymous'
        print(self.session.get(
            url=consumerUrl, verify=False).json())
        KONG_ANONYMOUS = self.session.get(
            url=consumerUrl, verify=False).json()['id']
        valueDic = {}
        valueDic['KONG_ANONYMOUS'] = KONG_ANONYMOUS
        valueDic['NAMESPACE'] = self.namespace
        if self.domain != None:
            valueDic['DOMAIN'] = self.domain
        if self.op_domain != None:
            valueDic['OP_DOMAIN'] = self.op_domain


        output = open((self.value_file), mode='wt')
        yaml.round_trip_dump(
            valueDic, output, default_flow_style=False, allow_unicode=True)
        output.close()

    def Render(self):
        serviceTmpl = listdir('./kong_configs/tmpl/service')
        routeTmpl = listdir('./kong_configs/tmpl/route')
        pluginTmpl = listdir('./kong_configs/tmpl/plugin')

        for svc in serviceTmpl:
            filePath =('%s/tmpl/service/%s') % (self.baseDir,svc)
            render_template(template=filePath,value_file=self.value_file,output='./kong_configs/output/service/'+svc)

        for rot in routeTmpl:
            filePath =('%s/tmpl/route/%s') % (self.baseDir,rot)
            render_template(template=filePath,value_file=self.value_file,output='./kong_configs/output/route/'+rot)

        for plg in pluginTmpl:
            filePath =('%s/tmpl/plugin/%s') % (self.baseDir,plg)
            render_template(template=filePath,value_file=self.value_file,output='./kong_configs/output/plugin/'+plg)

    def Delete(self, fields=None):
        defaultFields = {'services', 'routes', 'plugins'}
        if fields is None:
            fields =defaultFields
        if not(defaultFields & set(fields)):
            raise Exception('only {0}'.format(defaultFields))

        pluginOutput = listdir('./kong_configs/output/plugin')
        for plg in pluginOutput:
            filePath =('%soutput/plugin/%s') % (self.baseDir,plg)
            jsonData = json.load(
                open(filePath, mode='rt', encoding='utf-8'))
            for item in jsonData:
                if item['route'] != None:
                    pluginType = 'routes'
                    attachTo = item['route']['name']
                elif item['service'] != None:
                    pluginType = 'services'
                    attachTo = item['service']['name']

                getUrl = '%s/%s/%s/plugins' % (self.clusterKong,pluginType,attachTo)
                # pluginId = self.session.get(url=getUrl,verify=False).json()['data'][0]['id']
                print(getUrl)
                pluginId=None
                print(self.session.get(url=getUrl,verify=False).json())
                for i in self.session.get(url=getUrl,verify=False).json()['data']:
                    if item['name'] == i['name']:
                        pluginId = i['id']
                if pluginId is not None:
                    deleteUrl = '%s/plugins/%s' % (self.clusterKong,pluginId)
                    putResult = self.session.delete(url=deleteUrl, json=item, verify=False)

                    if putResult.status_code == 409:
                        Desc = 'Duplicate item.'
                    elif putResult.status_code == 200:
                        Desc = 'Updated.'
                    elif putResult.status_code == 201:
                        Desc = 'Created.'
                    else:
                        Desc = putResult.text
                    logger.info('[KONG] KONGA API > plugin: KongRespone: %s, Desc: %s, pluginName: %s, Patch to %s: %s' % (
                        putResult.status_code, Desc, item['name'], pluginType, attachTo))

        routeOutput = listdir('./kong_configs/output/route')
        for rot in routeOutput:
            filePath =('%soutput/route/%s') % (self.baseDir,rot)
            jsonData = json.load(open(filePath, mode='rt', encoding='utf-8'))
            routeUrl = self.clusterKong + '/routes/' + jsonData['name']
            result = self.session.delete(url=routeUrl, json=jsonData, verify=False)
            attachTo = jsonData['service']['name']
            if result.status_code == 204:
                Desc = 'ok'
            else:
                Desc = result.text
            logger.info('[KONG] KONGA API > Route   :KongRespone: %s, Desc: %s , routeName:  %s, Attach to svc: %s' % (
                result.status_code, Desc,jsonData['name'], attachTo))

        serviceOutput = listdir('./kong_configs/output/service')

        for svc in serviceOutput:
            filePath = ('%soutput/service/%s') % (self.baseDir, svc)
            with open(filePath, mode='rt', encoding='utf-8') as f:
                jsonData = json.load(f)
                svcUrl = "{0}/services/{1}".format(self.clusterKong, jsonData.get('name'))
                result = self.session.delete(url=svcUrl, verify=False)
                if result.status_code == 204:
                    Desc = 'delete ok'
                else:
                    Desc = result.text
                logger.info('[KONG] KONGA API > Service : KongRespone: %s, Desc: %s , svcName:    %s, Host: %s' % (
                    result.status_code, Desc,jsonData['name'], jsonData['host']))

    def Import(self):
        serviceOutput = listdir('./kong_configs/output/service')
        routeOutput = listdir('./kong_configs/output/route')
        pluginOutput = listdir('./kong_configs/output/plugin')
        # svcUrl = "https://10.0.169.20:31102/services/d646cfbc-bab1-48b6-9a16-c8c51c855f2e"
        # result = self.session.get(url=svcUrl, verify=False)

        for svc in serviceOutput:
            filePath =('%soutput/service/%s') % (self.baseDir,svc)
            jsonData = json.load(
                open(filePath, mode='rt', encoding='utf-8'))
            # if jsonData.get('id') == 'd646cfbc-bab1-48b6-9a16-c8c51c855f2e':
            svcUrl = self.clusterKong + '/services/' + jsonData['id']
            # logger.info('[KONG] PostURL: %s' % svcUrl)
            logger.info('PUT URL: %s' % svcUrl)
            result = self.session.put(
                url=svcUrl, json=jsonData, verify=False)
            if result.status_code == 409:
                Desc = 'Duplicate item.'
            elif result.status_code == 200:
                Desc = 'Updated.'
            elif result.status_code == 201:
                Desc = 'Created.'
            else:
                Desc = result.text
            logger.info('[KONG] KONGA API > Service : KongRespone: %s, Desc: %s , svcName:    %s, Host: %s' % (
                result.status_code, Desc,jsonData['name'], jsonData['host']))

        for rot in routeOutput:
            filePath =('%soutput/route/%s') % (self.baseDir,rot)
            jsonData = json.load(open(filePath, mode='rt', encoding='utf-8'))
            routeUrl = self.clusterKong + '/routes/' + jsonData['name']
            attachTo = jsonData['service']['name']
            # if attachTo == 'console-core-latest.nh3gowg':
            result = self.session.put(url=routeUrl, json=jsonData, verify=False)
            if result.status_code == 409:
                Desc = 'Duplicate item.'
            elif result.status_code == 200:
                Desc = 'Updated.'
            elif result.status_code == 201:
                Desc = 'Created.'
            else:
                Desc = result.text

            logger.info('[KONG] KONGA API > Route   :KongRespone: %s, Desc: %s , routeName:  %s, Attach to svc: %s' % (
                result.status_code, Desc,jsonData['name'], attachTo))

        for plg in pluginOutput:

            filePath =('%soutput/plugin/%s') % (self.baseDir,plg)
            jsonData = json.load(
                open(filePath, mode='rt', encoding='utf-8'))
            for item in jsonData:
                if item['route'] != None:
                    pluginType = 'routes'
                    attachTo = item['route']['name']
                elif item['service'] != None:
                    pluginType = 'services'
                    attachTo = item['service']['name']

                # if attachTo == 'console-core-latest.nh3gowg':
                pluginUrl = self.clusterKong + '/plugins'
                result = self.session.post(url=pluginUrl, json=item, verify=False)

                getUrl = '%s/%s/%s/plugins' % (self.clusterKong, pluginType, attachTo)
                # pluginId = self.session.get(url=getUrl,verify=False).json()['data'][0]['id']
                print(getUrl)
                print(self.session.get(url=getUrl, verify=False).json())
                for i in self.session.get(url=getUrl, verify=False).json()['data']:
                    if item['name'] == i['name']:
                        pluginId = i['id']
                putUrl = '%s/plugins/%s' % (self.clusterKong,pluginId)
                putResult = self.session.put(url=putUrl, json=item, verify=False)

                # logger.info('[KONG] DUMP putURL: %s putJSON: %s' % (putUrl,item))
                if result.status_code == 409:
                    Desc = 'Duplicate item.'
                elif result.status_code == 200:
                    Desc = 'Updated.'
                elif result.status_code == 201:
                    Desc = 'Created.'
                else:
                    Desc = result.text
                logger.info('[KONG] KONGA API > plugin: KongRespone: %s, Desc: %s, pluginName: %s, Attach to %s: %s ' % (
                    result.status_code, Desc,item['name'], pluginType, attachTo, ))

                if putResult.status_code == 409:
                    Desc = 'Duplicate item.'
                elif putResult.status_code == 200:
                    Desc = 'Updated.'
                elif putResult.status_code == 201:
                    Desc = 'Created.'
                else:
                    Desc = putResult.text
                logger.info('[KONG] KONGA API > plugin: KongRespone: %s, Desc: %s, pluginName: %s, Patch to %s: %s' % (
                    putResult.status_code, Desc, item['name'], pluginType, attachTo))

    def importConsumers(self):
        consumersTmpl = listdir('./kong_configs/tmpl/consumers')
        for name in consumersTmpl:
            filePath = ('%s/tmpl/consumers/%s') % (self.baseDir, name)
            with open(filePath, 'rt') as f:
                consumers = json.loads(f.read())
                for data in consumers:
                    username_list = data['username'].split('.')
                    username_list.pop()
                    username_list.append(self.namespace)
                    data['username'] = '.'.join(username_list)
                    Url = self.clusterKong + '/consumers/' + data['username']
                    res = self.session.put(Url, json=data, verify=False)
                    print(res.status_code,res.content)




if __name__ == '__main__':
    try:
        # clusterKong= input('Kong Admin url [e.g: https://kong.uisee.com:30001]: ')
        # domain= input('Domain [e.g: console.uisee.com]: ')
        # op_domain= input('Operator domain [e.g: console.uisee.com]: ')
        # namespace= input('namespace: ')
        clusterKong= 'https://10.0.169.20:31102'
        domain= 'double-live-test.uisee.com'
        op_domain= None
        namespace= 'nh3gowg'
        print('\nPlease confirm your config:\nclusterKong: %s\ndomain: %s\nop_domain: %s\nnamespace: %s\n' %(clusterKong,domain,op_domain,namespace))
        while True:
            # confirm = input('Confirm: [N/y]: ')
            confirm = 'y'
            if confirm.strip(' ') == 'y':
                kongimporter = KongaImporter(clusterKong=clusterKong, domain=domain, op_domain=op_domain, namespace=namespace)
                # kongimporter.Render()
                # try:
                #     kongimporter.Delete()
                # except Exception as e:
                #     logger.error('delete {} data from {} error'.format(namespace, clusterKong))
                # kongimporter.Import()
                kongimporter.importConsumers()
                logger.info('Kong import success')
                break
            elif confirm.strip(' ') == "":
                continue
            else:
                print('Bye.')
                break
    except KeyboardInterrupt:
        print('\n"Ctrl+c" catched, Bye.')
