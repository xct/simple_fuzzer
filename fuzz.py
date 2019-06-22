#!/usr/bin/python3
import os
import argparse
import subprocess
import shutil
import re
import time
import tempfile
import asyncio
import random
import sys
from generator.genetic import Genetic

dynamorioHOME = "/home/xct/dynamorio/build64"

class Module():
    def __init__(self, id, containing_id, start, end, entry, offset, path):
        self.id = id
        self.containing_id = containing_id
        self.start = start
        self.end = end
        self.entry = entry
        self.offset = offset
        self.path = path


class BasicBlock():
    def __init__(self, module_id, start, size):
        self.module_id = module_id
        self.start = start
        self.size = size


class Trace():
    def __init__(self, modules, bbs, signal, out):
        self.modules = modules
        self.bbs = bbs
        self.signal = signal
        self.output = out


class EdgeMap():
    def __init__(self):
        self.edges = dict()
        self.bbs = dict()
        self.verbose = False

    
    def update(self, addr1, addr2):
        cov = False
        addr1 = self.store(addr1)
        addr2 = self.store(addr2)
        e = addr1 ^ addr2
        if e not in self.edges:
            cov = True
            self.edges[e] = 0
            if self.verbose:
                print("    +Cov")
        else:
            self.edges[e] += 1
        return cov
  

    def store(self, addr):
        if addr not in self.bbs:
            self.bbs[addr] = random.randint(0, 0xFFFFFFFF)   
            #print("New Address")     
        return self.bbs[addr]


    def get(self, num):
        for k, v in self.bbs.items():
            if v == num:
                return self.bbs[k]
        assert(num in self.bbs.values())


class Fuzz():
    def __init__(self, wd, seed_dir, target):
        self.wd = wd + "/" + target.split(' ')[0].rsplit('/')[-1]
        self.wd = self.wd.replace("//","/")
        self.trace_dir = self.wd + "/traces"
        self.input_dir = self.wd + "/inputs"
        self.queue_dir = self.wd + "/queue"
        self.cur_input = self.wd+"/cur_input"
        print("[+] Writing to "+self.wd)
        if not os.path.exists(seed_dir):
            print("[-] Seed directory does not exist, exiting..")
            exit(0)
        self.seed_dir = seed_dir
        self.target = target
        self.map = EdgeMap()
        self.procs = []


    async def run(self, target):
        cmd = [""]
        for i in target.split(" "):
            cmd.append(i)

        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE)
        await proc.wait()


    async def run_and_trace(self, target):
        modules = []
        bbs = []       
        name = target.split(" ")[0].rsplit("/")[-1]
        # generate trace
        cmd = [dynamorioHOME+"/bin64/drrun", "-t", "drcov", "-dump_text","--"]
        for i in target.split(" "):
            cmd.append(i)
        #print(*cmd)
        proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE)
        out, _ = await proc.communicate()
        # print(out)
        # read result
        pid = str(proc.pid)
        if len(pid) < 5:
            pid = '0'+pid
        fname = "drcov."+name+"."+pid+".0000.proc.log"
        with open(self.trace_dir+"/"+fname, 'r') as f:
            lines = f.readlines()
            for i, line in enumerate(lines):
                # skip first 4 lines
                if i < 4:
                    continue
                # parse modules
                m = re.match(r'\s*(\d+),\s*(\d+),\s*([x0-9a-f]+),\s*([x0-9a-f]+),\s*([x0-9a-f]+),\s*([x0-9a-f]+),\s*([a-z0-8\.\/]+)', line)
                if m != None and len(m.groups()) == 7:
                    m = Module(m.group(1),m.group(2),m.group(3),m.group(4),m.group(5),m.group(6),m.group(7))
                    modules.append(m)
                # parse basic blocks
                m = re.match(r'\s*module\[\s*([0-9]+)\]:\s*([x0-9a-f]+),\s*([x0-9a-f]+)', line)
                if m != None and len(m.groups()) == 3:
                    bb = BasicBlock(m.group(1),m.group(2),m.group(3))
                    bbs.append(bb)
        #print("[+] Trace has "+str(len(modules))+" modules and "+str(len(bbs))+" basic blocks")
        return Trace(modules, bbs, proc.returncode, out)


    def update_state(self, trace):
        ''' Updates the state and returns true if new coverage was
        generated or segfault / sigabrt occured
        ''' 
        metric = False       
        if trace.signal == 11:
            print("[!] Segfault")
            return True
        elif trace.signal == 6:
            print("[!] Sigabrt")
            return True
        last = -1
        for bb in trace.bbs:
            addr = -1
            for module in trace.modules:
                if module.id == bb.module_id:                    
                    addr = int(module.start,16) + int(bb.start,16)
                    if last != -1:
                        #print(f"{hex(last)}->{hex(addr)}")
                        cov = self.map.update(last, addr)
                        if cov and not metric:
                            metric = cov
                    last = addr
            if addr == -1:
                print("[-] Error in update_state")
                exit(-1)
        if metric:
            print(f"Output: {trace.output}")
        return metric
           

    def main(self):
        # setup directories
        if not os.path.exists(self.wd):
            os.mkdir(self.wd)
            os.mkdir(self.trace_dir)
            os.mkdir(self.queue_dir)
        else:
            choice = input("[?] Directory "+self.wd+" exists. Delete ? [y/n] ")
            if choice == 'y':
                shutil.rmtree(self.wd)
                os.mkdir(self.wd)
                os.mkdir(self.trace_dir)
                os.mkdir(self.queue_dir)
            else:
                print("[-] Exiting")
                exit(0)
        # create working file
        open(self.cur_input, 'a').close()
        # copy over seeds
        shutil.copytree(self.seed_dir, self.input_dir)        
        
        # generate traces for seed files
        os.chdir(self.trace_dir)
        for fname in os.listdir(self.input_dir):
            # replace placeholder
            fname = self.input_dir+"/"+fname
            target = self.target.replace("@@",fname,1)
            trace = asyncio.run(self.run_and_trace(target))
            self.update_state(trace)
        os.chdir(self.wd)        

        # start fuzzing      
        generator = Genetic(self.seed_dir, self.queue_dir)  # use genetic generator
        os.chdir(self.trace_dir)    
        self.map.verbose = True
        print("[+] Running fuzzer..")    
        for i in range(1000000):
            with open(self.cur_input, 'r+b') as f:
                sample = generator.generate()
                #print(sample)
                f.write(sample)
                f.seek(0)
                target = self.target.replace("@@",self.cur_input,1)                
                trace = asyncio.run(self.run_and_trace(target))
                cov = self.update_state(trace)
                generator.feedback(sample, cov)
        os.chdir(self.wd)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("working_directory")
    parser.add_argument("seed_directory")
    parser.add_argument("target_binary")
    args = parser.parse_args()
    fuzz = Fuzz(args.working_directory, args.seed_directory, args.target_binary)
    fuzz.main()
