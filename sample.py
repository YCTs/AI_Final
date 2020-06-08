import argparse
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.distributions import Categorical

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

class Environment:

    def __init__(self):

        self.is_terminal = False

        self._start = torch.tensor([0 ,0, 0, 0, 0], device=device)

    def init_state(self):
        """ We need to define this function to initialize the environment.

        Returns:
            The starting state of the environment

        """

        self.is_terminal = False

        return self.start

    def step(self, s, a, t):

        """ We need to define this function as the transition function.(SEIR....)

        Args:
            s: current state
            a: action taken by agent in current state
            t: time

        Returns:
            next_sate (torch tensor ): The next state (aka  s' ) given by s and a .
            reward (int) : reward of (s, a, s')
            is_terminal (boolean) : if next_state a terminal state

        """
        
        next_sate = torch.tensor([0 ,1, 2, 3, 4, 6, 7], device=device).float()

        reward = 1

        return next_sate, reward, self.is_terminal

    def obeserved_state(self, state):
        """ To transform a global state to an obsevable state for agent.

        Args:
            state : global state

        Returns:
            observed_state : obsevable state for agent

        """

        observed_state = torch.tensor([0 ,1, 2, 3, 4], device=device).float()

        return observed_state

    @property
    def start(self):
        return self._start


class Agent(nn.Module):
    def __init__(self, dim_input, dim_output, max_actions, init_legal_actions):

        super(Agent, self).__init__()

        self.init_legal_actions = init_legal_actions

        self.legal_actions = self.init_legal_actions.copy()

        self.log_probs = []

        self.rewards = []

        self.action_embeddings = nn.Embedding(max_actions, dim_output)

        self.net = nn.Sequential(
            nn.Linear(dim_input, 8),
            nn.Dropout(0.1),
            nn.Linear(8, dim_output)
        )

    def init_agent(self):

        self.legal_actions = self.init_legal_actions.copy()

        self.log_probs = []

        self.rewards = []


    def forward(self, state):

        state_vector = self.net(state)

        actions = torch.tensor(self.legal_actions, device=device)

        actions_vectors = self.action_embeddings(actions)

        scores = torch.matmul(actions_vectors, state_vector.unsqueeze(1)).squeeze()

        return F.softmax(scores, dim=0)

    def select_actions(self, scores):

        distribution = Categorical(scores)

        action = distribution.sample()

        self.log_probs.append(distribution.log_prob(action))
        
        return action.item()


class Simulatoin:

    def __init__(self, agent:Agent, environment:Environment):

        self.agent = agent

        self.environment = environment

        self.gamma = 0.9

        self.optimizer = optim.Adam(self.agent.parameters(), lr=1e-3)
    
    def policy_gradient_update(self):

        policy_loss = 0
        accumulated_rewards = []

        # v_t = r_t + gammar*v_t+1
        # v_T = 0
        # agent.rewards : [r0, r1, r2, .......]

        v = 0 # V_T

        for r in self.agent.rewards[::-1]:

            v = r + self.gamma * v

            accumulated_rewards.insert(0, v)

        accumulated_rewards = torch.tensor(accumulated_rewards, device=device)

        accumulated_rewards = (accumulated_rewards - accumulated_rewards.mean()) / (accumulated_rewards.std() + 1e-9)

        for log_prob, r in zip(self.agent.log_probs, accumulated_rewards):
            
            policy_loss += (-log_prob * r)

        self.optimizer.zero_grad()
        
        policy_loss.backward()

        self.optimizer.step()


    def episodes(self, max_episodes=3, max_steps=10):

        for episode in range(max_episodes):

            state = self.environment.init_state()

            state_observed = self.environment.obeserved_state(state)

            reward_episode = 0

            for t in range(max_steps):

                actions_probs = self.agent.forward(state_observed)

                action = self.agent.select_actions(actions_probs)

                state, reward, is_terminal = self.environment.step(state, action, t=0)

                state_observed = self.environment.obeserved_state(state)

                self.agent.rewards.append(reward)

                reward_episode+=reward

                

                if is_terminal:

                    break

            self.policy_gradient_update()

            self.agent.init_agent()

def main():


    init_legal_actions = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

    agent = Agent(5, 3, 10, init_legal_actions)

    env = Environment()

    game = Simulatoin(agent, env)

    game.episodes()




if __name__ == "__main__":
    main()