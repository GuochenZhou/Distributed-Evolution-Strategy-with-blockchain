"""
Blockchain for Distributed Evolution Strategy
Client script
"""
import blockchain as bl
import requests
from MyEncoder import *
from net_supply import *
from pypoplib.function_supply import *
from pypoplib.lmmaes import LMMAES


class Client(object):
    def __init__(self, node_id, server_address, n_islands=20):
        """
        Client for our distributed blockchain es
        :param node_id: Id of the client
        :param server_address: Address of the server
        :param n_islands: Maximum island algorithm may use
        """
        self.node_id = node_id
        self.server_address = server_address
        self.n_islands = n_islands
        self.problem = None
        self.options = None
        self.blockchain = bl.Blockchain()

    def get_global_option(self):
        """
        Get global options from the server and choose one to optimize our inner-es
        """
        response = requests.get('http://{address}/global_option'.format(address=self.server_address))
        return response.json()['global_options']

    def send_option(self, option):
        """
        Send option to the server
        :param option: Option including s, tm, c_s, sigma, x, y
        """
        requests.post('http://{address}/new_option'.format(address=self.server_address),
                      json=json.dumps({"option": option}, cls=MyEncoder))

    def get_chain(self):
        """
        Get the full chain from server
        """
        response = requests.get('http://{node}/chain'.format(node=self.server_address))
        if response.status_code == 200:
            return response.json()['chain']

    def get_server_status(self):
        """
        Get the status of the server to judge whether to stop
        """
        response = requests.get('http://{node}/status'.format(node=self.server_address))
        if response.status_code == 200:
            return response.json()

    def get_new_block(self):
        """
        Get the newest block of the chain
        """
        response = requests.get('http://{node}/new_block'.format(node=self.server_address))
        if response.status_code == 200:
            return response.json()['block']

    def get_final_answer(self):
        """
        Get the final answer of the outer-es
        """
        response = requests.get('http://{node}/final_answer'.format(node=self.server_address))
        if response.status_code == 200:
            return response.json()['x'], response.json()['y']

    def register_new_block(self):
        """
        Register new block into the blockchain
        """
        block_data = self.get_new_block()
        block = bl.Block(block_data['index'], block_data['options'],
                         block_data['timestamp'], block_data['previous_hash'], block_data['nonce'])
        proof = block_data['hash']
        if_add = self.blockchain.add_block(block, proof)
        if not if_add:
            raise Exception("The block is broken!")

    def get_task(self):
        response = requests.get('http://{node}/task'.format(node=self.server_address))
        if response.status_code == 200:
            problem = response.json()["problem"]
            options = response.json()["options"]
            self.problem = {
                "fitness_function": get_function(problem['function_name']),
                "ndim_problem": problem['ndim_problem'],
                "lower_boundary": problem['lower_boundary'],
                "upper_boundary": problem['upper_boundary']
            }
            self.options = options
            self.n_islands = options['n_islands']
        else:
            print("ERROR: Can't get task")

    def register_node(self):
        """
        Register node in the blockchain
        """
        current_ip = get_host_ip()
        requests.post('http://{address}/register_inner_new'.format(address=self.server_address),
                                   json=({"node_address": current_ip}))
        self.blockchain.register_node(self.server_address, True)
        chain_data = self.get_chain()
        self.blockchain.add_blocks(chain_data)

    def work(self):
        """
        Function to check the status and wait according to output
        """
        self.register_node()
        self.get_task()
        while True:
            status = self.get_server_status()
            if status['length'] > len(self.blockchain.chain):
                self.register_new_block()
            if status['status'] == "stop":
                x, y = self.get_final_answer()
                print("The optimizer have get the final answer")
                print("The final answer is:")
                print("x =", x)
                print("y = ", y)
                break
            temp_options = self.get_global_option()
            temp_option = dict(temp_options[np.random.randint(self.n_islands)])
            self.options['s'], self.options['tm'] = np.array(temp_option['s']), np.array(temp_option['tm'])
            self.options['c_s'], self.options['sigma'] = temp_option['c_s'], temp_option['sigma']
            optimizer = LMMAES(self.problem, self.options)
            result = optimizer.optimize()
            option = {"node_address": self.node_id,
                      's': result['s'].tolist(),
                      'tm': result['tm'].tolist(),
                      'c_s': result['c_s'],
                      'sigma': result['sigma'],
                      'runtime': result['runtime'],
                      'x': result['mean'].tolist(),
                      'y': result['best_so_far_y']}
            self.send_option(option)


if __name__ == '__main__':
    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument('-s', '--server', default='10.26.137.51:5000', help='Address of server')
    parser.add_argument('-i', '--id', default=0, help='Id of node')
    args = parser.parse_args()
    client = Client(args.id, args.server)
    print("-----------")
    print("Server Address info:")
    print(client.server_address)
    client.work()
