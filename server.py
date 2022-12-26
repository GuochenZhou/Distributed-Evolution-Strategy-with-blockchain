"""
Blockchain for Distributed Evolution Strategy
Server script
"""
import time

from distributed_lmmaes import DistributedES as Solver
import pypoplib.base_functions as cf
from flask import Flask, request, jsonify
from uuid import uuid4
from threading import Thread, Event
from MyEncoder import *
import blockchain as bl

STOP_EVENT = Event()

status = {
    's': "receiving",
    'id': str(uuid4()).replace('-', ''),
    'blockchain': None,
    'address': "",
    'solver': None,
    }

app = Flask(__name__)


# endpoint to get server status
@app.route('/status', methods=['GET'])
def get_status():
    response = {
        'status': status['s'],
        'length': len(status['blockchain'].chain)
    }
    return jsonify(response), 200


# endpoint to submit a new option
@app.route('/new_option', methods=['POST'])
def new_option():
    tx_data = json.loads(request.get_json())
    request_fields = ["option"]
    for field in request_fields:
        if not tx_data.get(field):
            return "Invalid option data", 404
    temp_option = tx_data["option"]
    option = bl.Option(node_address=temp_option['node_address'],
                       s=np.array(temp_option['s']),
                       tm=np.array(temp_option['tm']),
                       c_s=temp_option['c_s'],
                       sigma=temp_option['sigma'],
                       x=np.array(temp_option['x']),
                       y=np.array(temp_option['y']))
    print(option.y)
    status['solver'].time_function_evaluations += temp_option['runtime']
    print(status['solver'].time_function_evaluations)
    status['blockchain'].add_current_option(option)
    if temp_option['runtime'] < status['solver'].island_max_runtime:
        mine_options()
        print("Already achieved threshold")
        status['solver'].best_so_far_x = temp_option['x']
        status['solver'].best_so_far_y = temp_option['y']
        status['solver'].runtime = temp_option['runtime']
        print("Runing time:")
        print(status['solver'].runtime)
        print("Final answer of x:")
        print(status['solver'].best_so_far_x)
        print("Final answer of y:")
        print(status['solver'].best_so_far_y)
        status['s'] = 'stop'
    return "Success", 201


# endpoint to add a new global option
@app.route('/global_option', methods=['GET'])
def renew_global_option():
    if len(status['blockchain'].current_options) >= status['solver'].n_islands:
        temp_time = time.time()
        status['solver'].renew_factors(status['blockchain'].current_options)
        results = status['solver'].iterate()
        status['blockchain'].renew_global_options(results)
        mine_options()
        status['solver'].runtime += time.time() - temp_time + status['solver'].island_max_runtime
        if status['solver']._check_terminations():
            print("Runing time:")
            print(status['solver'].runtime)
            print("Final answer of x:")
            print(status['solver'].best_so_far_x)
            print("Final answer of y:")
            print(status['solver'].best_so_far_y)
            status['s'] = 'stop'
    return json.dumps({"global_options": status['blockchain'].global_options}, cls=MyEncoder), 201


# endpoint to get the node's copy of chain
@app.route('/chain', methods=['GET'])
def get_chain():
    chain_data = []
    for block in status['blockchain'].chain:
        chain_data.append(block.__dict__)
    return json.dumps({"length": len(chain_data), "chain": chain_data}, cls=MyEncoder), 200


# endpoint to get the newest block
@app.route('/new_block', methods=['GET'])
def get_new_block():
    return json.dumps({"block": status['blockchain'].last_block().__dict__}, cls=MyEncoder), 200


# endpoint to get the final answer
@app.route('/final_answer', methods=['GET'])
def get_final_answer():
    return json.dumps({"x": status['solver'].best_so_far_x, "y": status['solver'].best_so_far_y}, cls=MyEncoder), 200


# endpoint to get task
@app.route('/task', methods=['GET'])
def get_task():
    task_problem = {
        "function_name": status['solver'].fitness_function.__name__,
        'ndim_problem': status['solver'].ndim_problem,
        'lower_boundary': status['solver'].lower_boundary,
        'upper_boundary': status['solver'].upper_boundary
    }
    task_options = {
        "max_runtime": status['solver'].island_max_runtime,
        "fitness_threshold": status['solver'].fitness_threshold,
        "seed_rng": status['solver'].seed_rng,
        "n_islands": status['solver'].n_islands,
        'verbose': status['solver'].island_verbose
    }
    print(status['solver'].fitness_function.__name__)
    return json.dumps({"problem": task_problem, "options": task_options}, cls=MyEncoder), 200


# register a new inner_node
@app.route('/register_inner_new', methods=['POST'])
def register_new_inner_node():
    node_address = request.get_json()["node_address"]
    if not node_address:
        return "Invalid address data", 400
    print("Register Node: ", node_address)
    status['blockchain'].inner_nodes.add(node_address)
    # return the new blockchain to the newly registered node
    return "Register new node", 400


# endpoint to mine
def mine_options():
    # consensus()
    result = status['blockchain'].mine()
    if not result:
        return "No option to mine"
    return "Block #{} is mined".format(status['blockchain'].last_block().index)


# endpoint to add block mined by other to the node's chain.
@app.route('/add_block', methods=['POST'])
def verify_and_add_block():
    block_data = request.get_json()
    block = bl.Block(block_data["index"], block_data["options"],
                  block_data["timestamps"], block_data["previous_hash"], block_data["nonce"])
    proof = block_data["hash"]
    added = status['blockchain'].add_block(block, proof)

    if not added:
        return "The block was discarded by the node", 400

    return "Block added to the chain", 201


# Get the longest chain in all nodes
def consensus():
    current_len = len(status['blockchain'].chain)
    longest_chain = None
    for node in status['blockchain'].inner_nodes:
        response = request.get('{}/chain'.format(node))
        length = response.json()['length']
        chain = response.json()['chain']
        if current_len < length and status['blockchain'].check_chain_validity(chain):
            current_len = length
            longest_chain = chain

        if longest_chain:
            status['blockchain'].chain = longest_chain
            return True
        else:
            return False


if __name__ == '__main__':
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000, type=int, help='port to listen on')
    parser.add_argument('-i', '--host', default='127.0.0.1', help='IP address of this miner')
    args = parser.parse_args()
    address = "{host}:{port}".format(host=args.host, port=args.port)
    status['address'] = address
    function = cf.step
    ndim_problem = 2000
    problem = {'fitness_function': function,
               'ndim_problem': ndim_problem,
               'upper_boundary': 10.0 * np.ones((ndim_problem,)),
               'lower_boundary': -10.0 * np.ones((ndim_problem,))}
    options = {'max_function_evaluations': np.Inf,
               'max_runtime': 3600,  # seconds
               'island_max_runtime': 180,
               'island_verbose': False,
               'fitness_threshold': 1e-10,
               'seed_rng': 2022,
               'record_fitness': False,
               'record_fitness_frequency': 2000,
               'verbose': False,
               'n_islands': 10,
               'sigma': 0.3}  # for ES
    status['solver'] = Solver(problem, options)
    status['blockchain'] = bl.Blockchain()
    status['blockchain'].create_genesis_block()
    status['blockchain'].renew_global_options(status['solver'].get_options())
    status['blockchain'].register_node(address, outer=True)
    app.run(host=args.host, port=args.port, threaded=True)
