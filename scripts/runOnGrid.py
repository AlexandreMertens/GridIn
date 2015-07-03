#! /usr/bin/env python

__author__ = 'sbrochet'

"""
Launch crab or condor and run the framework on multiple datasets
"""

from CRABAPI.RawCommand import crabCommand

import json
import copy
import os
import argparse

def get_options():
    """
    Parse and return the arguments provided by the user.
    """
    parser = argparse.ArgumentParser(description='Launch crab over multiple datasets.')
    parser.add_argument('-f', '--datasets', type=str, required=True, action='append', dest='datasets', metavar='FILE',
                        help='JSON files listings datasets to run over.')

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--mc', action='store_true', dest='mc', help='Run over MC datasets',)
    group.add_argument('--data', action='store_true', dest='data', help='Run over data datasets')

    parser.add_argument('-c', '--configuration', type=str, required=True, dest='configuration', metavar='FILE',
                        help='Analysis configuration file (including .py extension).')

    parser.add_argument('--submit', action='store_true', dest='submit',
                        help='Submit all the tasks to the CRAB server')

    options = parser.parse_args()

    if options.datasets is None:
        parser.error('You must specify a file listings the datasets to run over.')

    c = options.configuration
    if not os.path.isfile(c):
        # Try to find the configuration file
        filename = os.path.basename(c)
        path = os.path.join(os.environ['CMSSW_BASE'], 'src/cp3_llbb')
        c = None
        for root, dirs, files in os.walk(path):
            if filename in files:
                c = os.path.join(root, filename)
                break

        if c is None:
            raise IOError('Configuration file %r not found inside the cp3_llbb package' % filename)

    options.configuration = c

    return options

options = get_options()

datasets = {}
for dataset_file in options.datasets:
    with open(dataset_file) as f:
        datasets.update(json.load(f))

from cp3_llbb.GridIn.default_crab_config import create_config

config = create_config(options.mc)

def submit(dataset, opt):
    c = copy.deepcopy(config)

    c.General.requestName = opt['name']
    c.Data.publishDataName = opt['name']

    c.Data.inputDataset = dataset
    c.Data.unitsPerJob = opt['units_per_job']

    print("Submitting new task %r" % opt['name'])
    print("\tDataset: %s" % dataset)

    if options.data:
        c.Data.runRange = '%d-%d' % (opt['run_range'][0], opt['run_range'][1])
        c.Data.lumiMask = opt['certified_lumi_file'] if 'certified_lumi_file' in opt else\
            'https://cms-service-dqm.web.cern.ch/cms-service-dqm/CAF/certification/Collisions15/13TeV/Cert_246908-247381_13TeV_PromptReco_Collisions15_ZeroTesla_JSON.txt'

    # Create output file in case something goes wrong with submit
    with open('crab_' + opt['name'] + '.py', 'w') as f:
        f.write(str(c))

    if options.submit:
        crabCommand('submit', config=c)
    else:
        print('Configuration file saved as %r' % ('crab_' + opt['name'] + '.py'))

def submit_wrapper(args):
    submit(*args)

from multiprocessing import Pool
pool = Pool(processes=4)
pool.map(submit_wrapper, datasets.items())

