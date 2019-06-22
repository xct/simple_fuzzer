import random
import os
import binascii

class Genetic():
    def __init__(self, seed_dir, queue_dir):
        self.queue_dir = queue_dir
        self.samples = []
        for fname in os.listdir(seed_dir):
            with open(seed_dir+"/"+fname, 'rb') as f:
                content = f.read()
                self.samples.append(content)
        self.mutation_rate = 75 
        print(f"[+] Genetic generator initialized with {str(len(self.samples))} sample(s). Mutation Rate: {self.mutation_rate}%")
       

    def feedback(self, sample, coverage):
        # let samples that generate coverage live
        if coverage:
            self.addSample(sample)

    
    def addSample(self, sample):        
        self.samples.append(sample)
        print(f"Sample: {sample}")


    def generate(self):
        child = b''
        # selection (choose parents)
        left = random.choice(self.samples)
        right = random.choice(self.samples)
        # crossover 
        length = random.choice([len(left),len(right)])
        for i in range(length):
            coin = random.randint(0,1)
            if coin == 0 and len(left) >= i:
                child += left[i:i+1]
            elif coin == 1 and len(right) >= i:    
                child += right[i:i+1]
            else:
                if len(left) > len(right):
                    child += left[i:i+1]
                else:
                    child += right[i:i+1]
        # mutate length (and fill with random bytes)
        multiplier = random.uniform(1.0, 2.0)
        length = int(length * multiplier)
       
        # random mutation
        mutated = b''
        for i in range(length):
            coin = random.randint(0, 100)            
            if coin < self.mutation_rate: # n % chance
                mutated += os.urandom(1)                
            else:
                mutated += child[i:i+1]            
        child = mutated
        return child

        