# coding=utf-8
# This is a sample Python script.

# Press ⌃R to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for classes, files, tool windows, actions, and settings.

import os
import torch
import random
import argparse
from copy import deepcopy
import itertools
import numpy as np
import operator
#from scipy.stats import norm
#import scipy.special
import time
import sys
import copy
from math import ceil
import torch.nn as nn
import torch.nn.functional as F
sys.path.insert(0,'./venv/')
from WirelessEnv import RT_Multicast_Env
from DeepTOP import DeepTOP_RMAB
from Whittle_RTMulticast import Whittle_RTMulticast


def initializeEnv():
    global envs, state_dims, action_dims, nb_arms, global_seed
    for i in range(nb_arms):
        envs.append(RT_Multicast_Env(seed=global_seed + i*1000, p=0.8 - 0.6/nb_arms*i, d=10 + 2*i, N=5 + i))
        state_dims.append(2)
        action_dims.append(1)


def resetEnvs():
    global states, envs
    states.clear()
    for i in range(len(envs)):
        states.append(envs[i].reset())

def print_hi(name):
    # Use a breakpoint in the code line below to debug your script.
    print("Hi, {0}".format(name))  # Press ⌘F8 to toggle the breakpoint.


# Press the green button in the gutter to run the script.
if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='PyTorch on TORCS with Multi-modal')

    parser.add_argument('--mode', default='train', type=str, help='support option: train/test')
    parser.add_argument('--rate', default=0.001, type=float, help='learning rate')
    parser.add_argument('--prate', default=0.0001, type=float, help='policy net learning rate (only for DDPG)')
    parser.add_argument('--warmup', default=1000, type=int, help='time without training but only filling the replay memory')
    parser.add_argument('--discount', default=0.99, type=float, help='')
    parser.add_argument('--bsize', default=64, type=int, help='minibatch size')
    parser.add_argument('--rmsize', default=60000, type=int, help='memory size')
    parser.add_argument('--window_length', default=1, type=int, help='')
    parser.add_argument('--tau', default=0.001, type=float, help='moving average for target network')
    parser.add_argument('--ou_theta', default=0.15, type=float, help='noise theta')
    parser.add_argument('--ou_sigma', default=0.2, type=float, help='noise sigma')
    parser.add_argument('--ou_mu', default=0.0, type=float, help='noise mu')
    parser.add_argument('--validate_episodes', default=20, type=int, help='how many episode to perform during validate experiment')
    parser.add_argument('--max_episode_length', default=500, type=int, help='')
    parser.add_argument('--validate_steps', default=2000, type=int, help='how many steps to perform a validate experiment')
    parser.add_argument('--output', default='output', type=str, help='')
    parser.add_argument('--debug', dest='debug', action='store_true')
    parser.add_argument('--init_w', default=0.003, type=float, help='')
    parser.add_argument('--train_iter', default=200000, type=int, help='train iters each timestep')
    parser.add_argument('--epsilon', default=50000, type=int, help='linear decay of exploration policy')
    parser.add_argument('--seed', default=1, type=int, help='')
    parser.add_argument('--resume', default='default', type=str, help='Resuming model path for testing')
    parser.add_argument('--nb_arms', default=5, type=int, help='Number of arms')
    parser.add_argument('--budget', default=1, type=int, help='Budget')
    parser.add_argument('--agent_policy', default=0, type=int, help='Budget')


    args = parser.parse_args()
    global_seed = args.seed
    nb_arms = args.nb_arms
    budget = args.budget
    agent_policy = args.agent_policy
    # 0: DeepTOP; 1: Whittle_RTMulticast
    print(f'nb_arms = {nb_arms}, budget = {budget}')

    envs = []
    states = []
    state_dims = []
    action_dims = []
    initializeEnv()
    #initialize agent
    hidden = [8, 16, 16, 8]
    if agent_policy == 0:
        agent = DeepTOP_RMAB(nb_arms, budget, state_dims, action_dims, hidden, args)
    elif agent_policy == 1:
        agent = Whittle_RTMulticast(nb_arms, budget, state_dims, action_dims, hidden, args)
    agent.eval()
    resetEnvs()
    agent.reset(states)

    cumulative_reward = 0

    t = time.localtime()
    current_time = time.strftime("%H:%M:%S", t)
    print(current_time)
    iteration = 0
    num_step = 0

    for t in range(1000001):
        if t % 200000 == 0:
            iteration = iteration + 1
            num_step = 0
            print(f'iteration {iteration}')
            if agent_policy == 0:
                agent = DeepTOP_RMAB(nb_arms, budget, state_dims, action_dims, hidden, args)
            elif agent_policy == 1:
                agent = Whittle_RTMulticast(nb_arms, budget, state_dims, action_dims, hidden, args)
            agent.eval()
            resetEnvs()
            agent.reset(states)
 
        agent.is_training = True
        num_step = num_step + 1
        #resetEnvs()
        #agent.reset(states)

        # agent pick action ...
        if num_step <= args.warmup:
            action = agent.random_action()
        elif random.uniform(0, 1.0) < 0.05:
            action = agent.random_action()
        else:
            action = agent.select_action(states)

        # env response with next_state, reward, terminate_info
        next_state = []
        reward = []
        done = []
        info = []
        for i in range(len(envs)):
            next_state_i, reward_i, done_i, info_i = envs[i].step(action[i])
            next_state.append(next_state_i)
            reward.append(reward_i)
            done.append(done_i)
            info.append(info_i)
        next_state = deepcopy(next_state)

        # agent observe and update policy
        agent.observe(reward, next_state, done)
        if num_step > args.warmup:
            cumulative_reward = cumulative_reward + sum(reward)
            agent.update_policy()
            if( (num_step-args.warmup)%100 == 0 ):
                print(f'{cumulative_reward/100}')
                cumulative_reward = 0
        states = deepcopy(next_state)



# See PyCharm help at https://www.jetbrains.com/help/pycharm/
