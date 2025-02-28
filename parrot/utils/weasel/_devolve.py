"""
weasel
An Evolutionary Computing college assignment turned into a bot command
"""

import asyncio
import random
import string
import textwrap
from collections.abc import Callable
from typing import TypedDict

from parrot.utils import executor_function


DEFAULT_ALPHABET = string.ascii_lowercase


class Individual(TypedDict):
	genome: str
	fitness: int


type Population = list[Individual]
type Recombinator = Callable[[Individual, Individual], Population]
type Mutator = Callable[[Individual, float, str], Individual]


def get_alphabet(objective: str) -> str:
	"""Get the alphabet for the objective string.
	This is the ASCII letters plus any unique characters in the objective."""
	alphabet = set(DEFAULT_ALPHABET)
	for char in objective:
		alphabet.add(char)
	return "".join(alphabet)


def initialize_individual(genome: str, fitness: int) -> Individual:
	"""Create one individual."""
	return {"genome": genome, "fitness": fitness}


def initialize_pop(objective: str, pop_size: int) -> tuple[Population, str]:
	"""Create population to evolve."""
	alphabet = get_alphabet(objective)
	pop: Population = []
	for _ in range(pop_size):
		genome = "".join(random.choices(alphabet, k=len(objective)))
		pop.append(initialize_individual(genome, 0))
	return pop, alphabet


def one_point_crossover(parent1: Individual, parent2: Individual) -> Population:
	crossover_point = random.randint(1, len(parent1["genome"]) - 2)
	# crossover_point = random.randint(0, len(parent1["genome"]) - 1)
	child1 = (
		parent1["genome"][:crossover_point]
		+ parent2["genome"][crossover_point:]
	)
	child2 = (
		parent2["genome"][:crossover_point]
		+ parent1["genome"][crossover_point:]
	)
	return [initialize_individual(child1, 0), initialize_individual(child2, 0)]


def n_point_crossover(parent1: Individual, parent2: Individual) -> Population:
	raise NotImplementedError


def uniform_crossover(parent1: Individual, parent2: Individual) -> Population:
	raise NotImplementedError


"""Recombine two parents to produce two children."""
recombine_pair: Recombinator = one_point_crossover


def recombine_group(parents: Population, recombine_rate: float) -> Population:
	"""Recombine a whole group.

	Pair parents 1-2, 3-4, 5-6, etc.
	Recombine at rate, else clone the parents."""
	if len(parents[0]["genome"]) <= 2:
		# Recombination will do nothing (worse actually -- it will crash!) if
		# the genome is too short
		return parents
	for i in range(0, len(parents), 2):
		if random.random() < recombine_rate:
			child_pair = recombine_pair(parents[i], parents[i + 1])
			parents[i] = child_pair[0]
			parents[i + 1] = child_pair[1]
	return parents


def random_reset_mutation(
	parent: Individual, mutate_rate: float, alphabet: str
) -> Individual:
	genome = ""
	for i in range(len(parent["genome"])):
		if random.random() < mutate_rate:
			genome += random.choice(alphabet)
		else:
			genome += parent["genome"][i]
	return initialize_individual(genome, 0)


def creep_mutation(
	parent: Individual, mutate_rate: float, alphabet: str
) -> Individual:
	raise NotImplementedError


"""Mutate one individual, re-init its fitness to 0."""
mutate_individual: Mutator = random_reset_mutation


def mutate_group(
	children: Population, mutate_rate: float, alphabet: str
) -> Population:
	"""Mutate a whole Population, return the mutated group."""
	new_children = children.copy()
	for i in range(len(children)):
		new_children[i] = mutate_individual(children[i], mutate_rate, alphabet)
	return new_children


def evaluate_individual(objective: str, individual: Individual) -> None:
	"""Compute and modify the fitness for one individual.
	This is the count of shared characters (a string distance metric)."""
	for i in range(len(objective)):
		if individual["genome"][i] == objective[i]:
			individual["fitness"] += 1


def evaluate_group(objective: str, individuals: Population) -> None:
	"""Compute and modify the fitness for a population."""
	for individual in individuals:
		evaluate_individual(objective, individual)


def rank_group(individuals: Population) -> None:
	"""Sort a population by fitness, highest first."""
	individuals.sort(key=lambda x: x["fitness"], reverse=True)


def parent_select(individuals: Population, number: int) -> Population:
	"""Choose parents in direct probability to their fitness."""
	weights = [x["fitness"] for x in individuals]
	if all(w == 0 for w in weights):
		weights = [1] * len(weights)
	return random.choices(individuals, k=number, weights=weights)


def survivor_select(individuals: Population, pop_size: int) -> Population:
	"""Picks who gets to live!"""
	rank_group(individuals)
	return individuals[:pop_size]


@executor_function
def evolve(
	objective: str,
	pop_size: int = 3,
	fitness_percent: float = 1,
) -> str:
	"""A whole EC run, the main driver."""
	population, alphabet = initialize_pop(objective, pop_size)
	evaluate_group(objective=objective, individuals=population)
	rank_group(individuals=population)
	best_fitness = population[0]["fitness"]
	PERFECT_FITNESS = len(objective)
	fitness_goal = PERFECT_FITNESS * fitness_percent
	while best_fitness < fitness_goal:
		parents = parent_select(individuals=population, number=80)
		children = recombine_group(parents, recombine_rate=0.8)
		mutate_rate = (1 - (best_fitness / PERFECT_FITNESS)) / 5
		mutants = mutate_group(children, mutate_rate, alphabet)
		evaluate_group(objective=objective, individuals=mutants)
		everyone = population + mutants
		rank_group(individuals=everyone)
		population = survivor_select(individuals=everyone, pop_size=pop_size)
		if best_fitness != population[0]["fitness"]:
			best_fitness = population[0]["fitness"]
			# print("Iteration number", counter, "with best individual", population[0])
			# print("".join(population[0]["genome"]), end="\r")
			# print("".join(population[0]["genome"]))
	# print()
	return population[0]["genome"]


async def devolve(text: str) -> str:
	"""
	Partially evolve a string from randomness.

	Adds a certain special flavor of random noise to inputs, and that's the
	devolving it.
	"""
	fitness = random.uniform(0.6, 0.9)

	# Devolve chunks in parallel in groups of 60 characters
	async with asyncio.TaskGroup() as tg:
		tasks = [
			tg.create_task(evolve(chunk, fitness_percent=fitness))
			for chunk in textwrap.wrap(text, 60)
		]
	return "".join(task.result() for task in tasks)
