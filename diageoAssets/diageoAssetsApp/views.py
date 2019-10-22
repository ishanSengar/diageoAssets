from django.shortcuts import render
import requests
import json
import shutil
import os
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import time
import queue
from threading import Thread
from azure.storage.blob import BlockBlobService
from azure.storage.blob import PublicAccess
from django.http import HttpResponse

image_count = 0

block_blob_service = BlockBlobService(
    account_name='blobtestdemo', account_key='Tl8a4D/XDHUgcKwVPMeDQe/e+Un6lpDlJVU6LKM6FZ/KR8WNKe4wH3GxFeKz54zyY6+OClPqomZZLGRLEcuRVQ==')
container_name = 'diageobatch'
block_blob_service.create_container(container_name)


def decorator_function(func):
    def wrapper(*args,**kwargs):
        session = requests.Session()
        retry = Retry(connect=0, backoff_factor=0.2)
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('https://', adapter)

        return func(*args, session = session, **kwargs)
    return wrapper

def download_image(stri, q, session = None):

    while not q.empty():
        global image_count
        if not session:
            session = requests.Session()
        while not q.empty():
            try:
                urlArray = q.get(block=False)
                url = urlArray['image_url']
                id = urlArray['id']
                jsonText = urlArray['jsonText']
                r = session.get(url)
            except (requests.exceptions.RequestException, UnicodeError) as e:
                print(e)
                image_count += 1
                q.task_done()
                continue
            image_count += 1
            q.task_done()

            print('image', image_count)
            with open('image_{}.jpg'.format(image_count),
                    'wb') as f:
                f.write(r.content)
            with open(str(id)+'.txt', 'w') as outfile:
                json.dump(jsonText, outfile)
            block_blob_service.create_blob_from_path(
                container_name, str(id)+'/'+str(id)+'.jpg'.format(image_count), 'image_{}.jpg'.format(image_count))
            block_blob_service.create_blob_from_path(
                container_name, str(id) + '/' + str(id) + '.txt', str(id)+'.txt')



def hi(request):
    return render(request, 'diageoAssetsApp/home.html')

def getFiles(request):
    if request.method == 'POST':
        batchLink = request.POST.get('batchLink')

        start = time.time()

        URL = batchLink
        r = requests.get(url=URL,
                         headers={'X-Auth-Token': '51750c57ee13438e83c27e2314ce61de', 'Accept': 'application/json'})
        json_data = r.json()
        q = queue.Queue()
        for i in range(30):
            dict = {}
            dict['image_url'] = json_data['items'][i]['renditions']['downloadOriginal'][0]['href']
            dict['jsonText'] = json_data['items'][i]
            dict['id'] = json_data['items'][i]['id']
            q.put(dict)

        threads = []
        for i in range(10):
            t = Thread(target=download_image,
                       args=("ss", q))
            # t.setDaemon(True)
            threads.append(t)
            t.start()
        q.join()

        for t in threads:
            t.join()
            print(t.name, 'has joined')

        end = time.time()

        print('time taken: {:.4f}'.format(end - start))

        for i in range(image_count):
            os.remove('image_{}.jpg'.format(image_count))
            os.remove('image_{}.jpg'.format(image_count))


    return render(request, 'diageoAssetsApp/home.html')
