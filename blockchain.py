from hashlib import sha256
import json
import time
from urllib.parse import urlparse
from MyEncoder import *
from flask import Flask, jsonify, request
import requests


class Block(object):
    def __init__(self, index, options, timestamp, previous_hash, nonce=0):
        """
        Construct Block class
        :param index: Unique ID for block
        :param options: List of option
        :param timestamp: Time when generate the block
        :param previous_hash: Hash of the previous block in the chain
        :param nonce: Used for proof of work
        """
        self.index = index
        self.options = options
        self.timestamp = timestamp
        self.previous_hash = previous_hash
        self.nonce = nonce

    def compute_hash(self):
        """
        Return the hash of the block instance
        """
        block_string = json.dumps(self.__dict__, cls=MyEncoder, sort_keys=True)
        return sha256(block_string.encode()).hexdigest()


class Blockchain(object):
    difficulty = 1

    def __init__(self):
        self.chain = []
        self.current_options = []
        self.global_options = []
        self.inner_nodes = set()
        self.outer_node = None

    def create_genesis_block(self):
        """
        A function to create genesis block to the chain, which have index as 0
        """
        genesis_block = Block(0, [], time.time(), "0")
        genesis_block.hash = self.proof_of_work(genesis_block)
        self.chain.append(genesis_block)

    def register_node(self, address, outer=False):
        """
        Add a new node to the list of nodes
        :param address: <str> Address of node.
        :return: None
        """
        parsed_url = urlparse(address)
        if outer is False:
            self.inner_nodes.append(parsed_url.netloc)
        else:
            self.outer_node = parsed_url.netloc
        print("Register node: ", address)

    def add_block(self, block, proof):
        """
        A function that add block to the chain after verification
        Check if the proof is valid
        """
        if block.index != 0:
            previous_hash = self.last_block().hash
            if previous_hash != block.previous_hash:
                return False
        if not Blockchain.is_valid_proof(block, proof):
            return False
        block.hash = proof
        self.chain.append(block)
        return True

    def add_blocks(self, chain_dump):

        for block_data in chain_dump:
            block = Block(block_data['index'], block_data['options'],
                          block_data['timestamp'], block_data['previous_hash'], block_data['nonce'])
            proof = block_data['hash']
            if_add = self.add_block(block, proof)
            if not if_add:
                raise Exception("The chain dump is broken!")

    def add_current_option(self, option):
        # Add an option to the chain
        self.current_options.append(option)

    def renew_global_options(self, options):
        self.global_options = options

    def last_block(self):
        return self.chain[-1]

    def mine(self):
        """
        This block is work as an interface to add current options to the block
        """
        if not self.current_options:
            return False

        last_block = self.last_block()

        new_block = Block(index=last_block.index+1, options=self.current_options,
                          timestamp=time.time(), previous_hash=last_block.hash)
        self.current_options = []
        proof = self.proof_of_work(new_block)
        self.add_block(new_block, proof)
        return True

    @staticmethod
    def proof_of_work(block):
        """
        Function that tries different values to get a hash satisfy difficult creteria
        :return: return the hash that satisfy the difficulty
        """
        block.nonce = 0
        temp_hash = block.compute_hash()
        while not temp_hash.startswith('0' * Blockchain.difficulty):
            block.nonce += 1
            temp_hash = block.compute_hash()
        return temp_hash

    @classmethod
    def is_valid_proof(cls, block, block_hash):
        """
        Check if block's hash is valid
        """
        print("Calculate hash:", block.compute_hash())

        return block_hash.startswith('0' * Blockchain.difficulty) and block_hash == block.compute_hash()

    @classmethod
    def check_chain_validity(cls, chain):
        """
        Check whether the chain is valid
        :param chain: Blockchain for check
        :return: True for valid False for not
        """
        result = True
        previous_hash = '0'

        for block in chain:
            block_hash = block.hash
            delattr(block, "hash")

            if not cls.is_valid_proof(block, block_hash) or previous_hash != block.previous_hash:
                result = False
                break
            block.hash, previous_hash = block_hash, block_hash

        return result

# if __name__ == '__main__':
#     from argparse import ArgumentParser
#
#     parser = ArgumentParser()
#     parser.add_argument('-p', '--port', default=5000, type=int, help='port to listen on')
#     args = parser.parse_args()
#     port = args.port
#     app.run(host='127.0.0.1', port=port)
