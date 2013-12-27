import Queue
import json
import pprint
import random
from threading import Thread
from time import sleep, time
import requests

DEVICE_TYPE = 'huepy'
USERNAME = 'huepyhuepy'

get_bridge_ip = lambda bridge: bridge.get('internalipaddress')
endpoint = lambda bridge, path=None: 'http://' + get_bridge_ip(bridge) + ('/' + path if path else '')
auth_endpoint = lambda bridge, username, path=None: endpoint(bridge, 'api/' + username + ('/' + path if path else ''))

check_response = lambda resp: resp.json() if resp.status_code == 200 else None

REQUESET_QUEUE = Queue.Queue()
RESPONSE_QUEUE = Queue.Queue()

def writer(request_queue, response_queue):

    while True:
        args = request_queue.get()
        if args is None:
            break

        (tag, func, endpoint, args, kwargs) = args

        t1 = time()
        resp = func(endpoint, *args, **kwargs)
        t2 = time()

        rv = resp.json()

        print '>>>', tag, endpoint, 'took', '%.04f' % (t2-t1), 'ms ->', resp.status_code
        print '<<<', pprint.pformat(rv)
        response_queue.put(rv if resp.status_code == 200 else None)
        sleep(.1) # FIXME naive throttling

def start_writer():
    writer_thread = Thread(target=writer, args=(REQUESET_QUEUE, RESPONSE_QUEUE))
    writer_thread.daemon = True
    writer_thread.start()
    return writer_thread

def close_writer(writer_thread):
    REQUESET_QUEUE.put(None)
    writer_thread.join()

def givetake(tag, func, endpoint, *args, **kwargs):
    REQUESET_QUEUE.put((tag, func, endpoint, args, kwargs))
    return RESPONSE_QUEUE.get()

def GET(endpoint):
    return givetake('GET', requests.get, endpoint)

def POST(endpoint, data):
    return givetake('POST', requests.post, endpoint, data=json.dumps(data) if data is not None else None)

def PUT(endpoint, data):
    return givetake('PUT', requests.put, endpoint, data=json.dumps(data) if data is not None else None)

def discover_bridges():
    return GET('https://www.meethue.com/api/nupnp')

def register_user(bridge, device_type, username=None):
    data = {'devicetype': device_type}
    if username is not None:
        data['username'] = username
    return POST(endpoint(bridge, 'api'), data)

def get_config(bridge, username):
    return GET(auth_endpoint(bridge, username, 'config'))

def get_datastore(bridge, username):
    return GET(auth_endpoint(bridge, username))

def get_lights(bridge, username):
    return GET(auth_endpoint(bridge, username, 'lights'))

def get_light_state(bridge, username, id):
    return GET(auth_endpoint(bridge, username, 'lights/' + id))

def set_light_state(bridge, username, id, state):
    return PUT(auth_endpoint(bridge, username, 'lights/' + id + '/state'), state)

def turn_off(bridge, username, id):
    set_light_state(bridge, username, id, {'on': False, 'transitiontime': 10})

def turn_all_off(bridge, username):
    for id, state in get_lights(bridge, username).items():
        turn_off(bridge, username, id)

def main():

    writer_thread = start_writer()

    bridges = discover_bridges()
    bridge = bridges[0]

    if not get_lights(bridge, USERNAME):
        while not register_user(bridge, DEVICE_TYPE, USERNAME):
            print 'Press link button on bridge!!!'
            sleep(1)

    turn_all_off(bridge, USERNAME)
    sleep(3)

    resp = get_lights(bridge, USERNAME)

    hue_max = 65535

    hue = random.randint(0, hue_max)

    for id, light in resp.items():
        hue_slop = random.randint(-hue_max/10, hue_max/10)
        set_light_state(bridge, USERNAME, id, {
            'on': True,
            'bri': 0,
            'hue': hue + hue_slop,
            'sat': 255,
            'effect': 'colorloop',
            'transitiontime': 10
        })
        phase_slop = random.random()
        sleep(phase_slop)

    close_writer(writer_thread)

if __name__ == '__main__':
    main()