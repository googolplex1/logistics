#!/usr/bin/env python3

# Copyright 2020 Alexander Meier
# https://github.com/googolplex1
#
# This script was originally written to assist a friend with a simple logistics problem.
# It is NOT at all runtime optimized. Also it depends on a specific file as input.
# The purpose is completely educational.
#
# The script is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SCRIPT IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
# You should have received a copy of the GNU General Public License
# along with python-gsl. If not, see <http://www.gnu.org/licenses/>.


import pandas as pd
from random import randrange
import multiprocessing
import threading

lock = threading.Lock()

path = r'input.xlsx'

region = ['north_east', 'north', 'south']
cost = {}
res = []
total = []


def l2n(letter):
    return ord(letter) - 65


def n2l(number):
    return chr(number + 65)


def objective_fcn(x):
    # distance from regional hub to first stop
    track_len = df[x[0]][-1]
    for num, stop in enumerate(x[1:]):
        track_len += df[stop][l2n(x[num])]

    track_len += df[x[-1]][-1]
    return track_len * 0.8


def constrain_len(x):
    track_len = df[x[0]][-1]
    for num, stop in enumerate(x[1:]):
        track_len += df[stop][l2n(x[num])]

    track_len += df[x[-1]][-1]
    return 300 - track_len


def constrain_stops(x):
    return 5 - len(x)


def constrain_load(x):
    load = 0
    for stop in x:
        load += south.loc[stop, 'Demand']
    return 20 - load


def check_constrains(x):
    if constrain_load(x) < 0:
        return False
    if constrain_len(x) < 0:
        return False
    if constrain_stops(x) < 0:
        return False
    return True


def get_remaining(x, y):
    for i in y:
        x = [j for j in x if i not in j]
    return x


def calc_routes(l, output, cost):
    num = 0
    min_cost = None
    max_cost = None
    for s in cost.keys():
        curr_track = []
        curr_cost = 0
        curr_track.append(s)
        curr_cost += cost[s]
        remaining = get_remaining(list(cost.keys()), s)
        rem_dict = {i: cost[i] for i in cost.keys() if i in remaining}

        while (len(remaining) > 0):
            index = randrange(len(remaining))
            curr_track.append(list(rem_dict.items())[index][0])
            curr_cost += list(rem_dict.items())[index][1]
            remaining = get_remaining(list(rem_dict.keys()), list(rem_dict.items())[index][0])
            rem_dict = {i: rem_dict[i] for i in rem_dict.keys() if
                        i in get_remaining(list(rem_dict.keys()), curr_track[-1])}
        if min_cost is None or curr_cost < min_cost:
            min_cost = curr_cost
            l.acquire()
            try:
                output.put((curr_track, curr_cost))
            finally:
                l.release()
        if max_cost is None or curr_cost > max_cost:
            max_cost = curr_cost
            l.acquire()
            try:
                output.put((curr_track, curr_cost))
            finally:
                l.release()
        num += 1


def get_min_max_track(l, stop, output, results):
    total = []
    while (stop.qsize() == 0 and output.qsize()):
        if output.qsize():
            l.acquire()
            try:
                total.append(output.get())
            finally:
                l.release()

    min_cost = total[0][1]
    max_cost = total[0][1]
    min_track = total[0][0]
    max_track = total[0][0]
    for i in total:
        if i[1] < min_cost:
            min_cost = i[1]
            min_track = i[0]
        if i[1] > max_cost:
            max_cost = i[1]
            max_track = i[0]

    results.put({'min_cost': min_cost,
                 'min_track': min_track,
                 'max_cost': max_cost,
                 'max_track': max_track,
                 'num_routes_evaluated': len(total)})


def _add_hq(route, hq):
    _track = []
    for track in route:
        _track.append(f'{track}{hq}')
    return _track


def _get_route_info(route):
    g_len = 0
    g_demand = 0
    for track in route:
        t_len = 0
        t_demand = 0
        for i, stop in enumerate(track):
            if i == 0:
                _len = df[stop][-1]
            else:
                _len = df[stop][track[i - 1]]
            if i == len(track) - 1:
                city = 'Regional Hub'
                demand = 0
            else:
                city = south.loc[stop, 'City']
                demand = south.loc[stop, 'Demand']

            print(f'{stop}\t{city}\t{_len}\t{demand}\t{_len * 0.8}')
            t_len += _len
            t_demand += demand

        print(f'\tSum:\t{t_len}\t{t_demand}\t{t_len * 0.8}')
        g_len += t_len
        g_demand += t_demand
    print(f'\tTotal:\t{g_len}\t{g_demand}\t{g_len * 0.8}')


if __name__ == "__main__":
    for reg in region:
        print(f'Starting with region {reg}')

        south = pd.read_excel(path, sheet_name=reg)
        south_martix = pd.read_excel(path, sheet_name=f'{reg}_matrix')
        df = south_martix.drop(0).reset_index(drop=True).set_index('key').stack()
        south = south.reset_index(drop=True).set_index('key')

        cost = {}
        res = []

        for i in set(south.index):
            x = [i]
            if check_constrains(x):
                for j in set(south.index) - set(x):
                    x = [i, j]
                    if check_constrains(x):
                        for k in set(south.index) - set(x):
                            x = [i, j, k]
                            if check_constrains(x):
                                for m in set(south.index) - set(x):
                                    x = [i, j, k, m]
                                    if check_constrains(x):
                                        for n in set(south.index) - set(x):
                                            x = [i, j, k, m, n]
                                            if check_constrains(x):
                                                res.append(x)
                                            else:
                                                res.append([i, j, k, m])
                                    else:
                                        res.append([i, j, k])
                            else:
                                res.append([i, j])
                    else:
                        res.append([i])

        for x in res:
            cost[''.join(x)] = objective_fcn(x)
        print(f'Got {len(cost)} possible tracks')

        procs = 3

        jobs = []
        lock = multiprocessing.Lock()
        output = multiprocessing.Queue()
        results = multiprocessing.Queue()
        stop = multiprocessing.Queue()

        process_route = multiprocessing.Process(target=get_min_max_track, args=(lock, stop, output, results))

        for pro in range(0, procs):
            process = multiprocessing.Process(target=calc_routes, args=(lock, pro, output, cost))
            jobs.append(process)

        for jo in jobs:
            jo.start()

        process_route.start()

        for jo in jobs:
            jo.join()

        stop.put(1)
        process_route.join()
        _ = stop.get()

        print(f'Region {reg}: {results.get()}')
