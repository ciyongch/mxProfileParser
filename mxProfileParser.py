import json
import argparse
from collections import defaultdict
import sys


def add_args(parser):
    parser.add_argument("--file",
                        help="profile json file", default="profile.json")
    parser.add_argument("--full", action='store_true',
                        help="whether to dump full statistics along iteration perspective")
    parser.add_argument("--iteration", default=0, type=int,
                        help="whether to dump full statistics along iteration perspective")
    parser.add_argument("--op", default='conv', type=str,
                        help="Which opeator to be dumped")


def print_op_detail(cnt, dur, dur_list, name='conv', iteration=0):
    print ('opeator')
    print ('=' * 20)

    if (iteration <= 0):
        print ('ERROR: `iteration` must be specified when full mode is enabled.')
        sys.exit(0)

    if (len(dur_list) < 3):
        print ('ERROR: full mode requires more than 3 iterations statistics.')
        sys.exit(0)

    assert (name in cnt.keys())

    print ('{0: <38} {1: >16} {2: >16} {3: >16} {4: >16} {5: >16} '.format(
      'Name', 'Layer', '1st Time (ms)', '2nd Time (ms)', '3rd Time (ms)', 'Rest Time (ms)'))

    print ('{0: <38} {1: >16} {2: >16} {3: >16} {4: >16} {5: >16} '.format(
      '----', '-----', '-------------', '-------------', '-------------', '--------------'))

    total_count = cnt[name]
    total_time = dur[name] / 1000.0
    assert (total_count % iteration == 0)

    layer_num = total_count // iteration

    for i in range(layer_num):
        first_iter_ms = dur_list[name][i] / 1000.0
        second_iter_ms = dur_list[name][i + layer_num] / 1000.0
        third_iter_ms = dur_list[name][i + 2 * layer_num] / 1000.0

        rest_iter_dur = dur_list[name][(i + 3 * layer_num) : : layer_num]
        rest_iter_time_ms = sum(rest_iter_dur) / len(rest_iter_dur) / 1000.0

        print ('{0: <38} {1:16d} {2:16.3f} {3:16.3f} {4:16.3f} {5:16.3f} '.format(
          name, i, first_iter_ms, second_iter_ms, third_iter_ms, rest_iter_time_ms))

    print('\nTotal Time: {0:.3f}ms, Average Time: {1:.3f}ms'.format(
      total_time, total_time / total_count))


def print_all(cnt, dur, dur_list):
    print ('opeator')
    print ('=' * 20)

    print ('{0: <38} {1: >16} {2: >16} {3: >16} {4: >16} {5: >16} {6: >16}'.format(
      'Name', 'Total Count', 'Time (ms)', 'Min Time (ms)', 'Max Time (ms)', 'Avg Time (ms)',
      'Percentage'))
    print ('{0: <38} {1: >16} {2: >16} {3: >16} {4: >16} {5: >16} {6: >16}'.format(
      '----', '-----------', '---------', '-------------', '-------------', '-------------',
      '----------'))

    sorted_dur = sorted(dur.items(), key=lambda kv: kv[1], reverse=True)

    total_time = sum(dur.values())
    for i in range(len(cnt)):
        name = sorted_dur[i][0]
        total_count = cnt[name]
        time_ms = dur[name] / 1000.0
        min_time_ms = min(dur_list[name]) / 1000.0
        max_time_ms = max(dur_list[name]) / 1000.0
        avg_time_ms = time_ms / cnt[name]
        percentage = 100.0 * dur[name] / total_time

        print ('{0: <38} {1: >16} {2:16.3f} {3:16.3f} {4:16.3f} {5:16.3f} {6:15.2f}%'.format(
          name, total_count, time_ms, min_time_ms, max_time_ms, avg_time_ms, percentage))

    print('\nTotal OP Time: %.3f ms' % (total_time / 1000.0))


def init_table(events):
    ops = []
    cnt = {}
    dur = {}
    for i in range(len(events)):
        if events[i]['name'] != 'process_name' and \
           events[i]['name'] not in ops and \
           events[i]['cat'] == 'operator':
            ops.append(str(events[i]['name']))
            if events[i]['name'] not in cnt.keys():
                cnt.update({events[i]['name']: 0})
            if e[i]['name'] not in dur.keys():
                dur.update({events[i]['name']: 0})

    return ops, cnt, dur


def parse_all(events, ops, cnt, dur):
    assert isinstance(events, list)
    dur_list = defaultdict(list)
    for i in range(len(events)):
        if events[i]['name'] in ops:
            name = events[i]['name']
            if events[i]['ph'] == 'B' and \
               events[i+1]['name'] == name and \
               events[i+1]['ph'] == 'E':
                cnt[str(name)] += 1
                time_us = events[i+1]['ts'] - events[i]['ts']
                dur[str(name)] += time_us
                dur_list[str(name)].append(time_us)

    return ops, cnt, dur, dur_list


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="mxnet profile file analysis",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter) # noqa
    add_args(parser)
    args = parser.parse_args()
    f = open(args.file, 'r')
    j = json.load(f)
    e = j['traceEvents']

    ops, cnt, dur = init_table(e)
    ops, cnt, dur, dur_list = parse_all(e, ops, cnt, dur)

    if args.full is True:
        if args.op not in cnt:
            print ('ERROR: \'{0}\' is not in the list. You may want to select one of the following '
                   'ones {1}'.format(args.op, tuple(cnt.keys())))
        print_op_detail(cnt, dur, dur_list, args.op, args.iteration)
    else:
        print_all(cnt, dur, dur_list)
