import csv
import os
import subprocess
import sys, getopt
import random

from Config import *


def buildDocker():
    dock = open("buildDocker.sh", "w")
    dock.write("echo 'test_moa'\n")
    dock.write("docker-compose up -d\n")
    dock.write("docker build . -t test_moa\n")
    dock.close()
    subprocess.run(["chmod", "+x", "./buildDocker.sh"])
    succ_docker = subprocess.call(['sh', './buildDocker.sh'])
    if succ_docker == 0:
        print("|" * 60)
        print(f"DOCKER IS UP")
        print("|" * 60)

def createDir():
    subprocess.run(["mkdir", "stats"])
    subprocess.run(["mkdir", "results"])
    for di, d in enumerate(drifts):
        subprocess.run(["mkdir", f"results/{d}"])
        for o in positives:
            subprocess.run(["mkdir", f"results/{d}/{str(o)}"])
            for alg in algorithms:
                subprocess.run(["mkdir", f"results/{d}/{str(o)}/{alg}"])

def generateArff():

    test = open("generateStreams.sh", "w")
    test.write("mkdir drifts_arff\n")
    for i in range(n_exp):
        test.write(f"echo 'generating experiment {i} drifts'\n")
        for o in positives:
            for d in drifts:
                for s in speeds:
                    if not os.path.isfile(f'./drifts_arff/{d}-{s}-{o}-{i}.arff'):
                        test.write(f"java -Xmx14g -Xss50M -cp moa.jar -javaagent:sizeofag-1.0.4.jar moa.DoTask '"
                                   f'WriteStreamToARFFFile -s '
                                   f'(moa.dabrze.streams.generators.ImbalancedDriftGenerator -d {d}/{s},start=0,end=100000,value-start=0.0,value-end=1.0 -n 2 -m 0.{o} -s 0.5 -b 0.5 -r {seeds[i]}) -f '
                                   f"./drifts_arff/{d}-{s}-{o}-{i}.arff -m 100000' \n")

    test.close()
    subprocess.run(["chmod", "+x", "./generateStreams.sh"])
    succ_gen = subprocess.call(['sh', './generateStreams.sh'])
    if succ_gen == 0:
        print("|" * 60)
        print(f"TEST SUCCESSFUL")
        print("|" * 60)

def createTest():
    test = open("Experiments.sh", "w")

    for i in range(n_exp):
        for alg in algorithms:
            for o in positives:
                for s in speeds:
                    test.write(f"echo {i} {alg} {o} {s}\n")
                    for di, d in enumerate(drifts):

                        if "sudden" in s:
                            drift = "50000"
                        else:
                            drift = "45000 -j 10000"

                        l = f'(meta.{alg})'
                        if "ESOS" in alg:
                            l = f'(meta.{alg} -c (OS_ELM -b 100 -i 100 -p) -e (WELM -p -i 100))'

                        elif "CSMOTE" in alg:
                            l = f'(meta.{alg} -l trees.HoeffdingAdaptiveTree -w 100000)'

                        elif "Reb" in alg:
                            l = f'(meta.{alg} -l trees.HoeffdingAdaptiveTree)'

                        elif "Tree" in alg:
                            l = f'(trees.{alg})'

                        test.write(
                            f'sudo docker run --rm --name="{d}_{alg}_{s}_{str(o)}_{str(i)}" '
                            f'-v $(pwd)/results:/results test_moa bash -c '
                            f'"java -Xmx14g -Xss50M -cp moa.jar -javaagent:sizeofag-1.0.4.jar moa.DoTask \\"'
                            f'EvaluatePrequential -l {l} -s '
                            f'(ArffFileStream -f ./drifts_arff/{d}-{s}-{o}-{i}.arff) -e '
                            f'(WindowFixedClassificationPerformanceEvaluator -w {drift} -r -f -g) -i -1 -f 5000\\" '
                            f'1> ./results/{d}/{str(o)}/{alg}/{s}_{str(i)}_err.csv 2> ./results/{d}/{str(o)}/{alg}/{s}_{str(i)}.csv"\n')
    test.close()

def executeTest():
    subprocess.run(["chmod", "+x", "./Experiments.sh"])
    succ_test = subprocess.call(['sh', './Experiments.sh'])
    if succ_test == 0:
        print("|"*60 )
        print(f"EXPERIMENTS SUCCESSFUL")
        print("|" * 60)

def import_csv(csvfilename):
    data = []
    with open(csvfilename, "r") as scraped:
        reader = csv.reader(scraped, delimiter=',')
        row_index = 0
        for row in reader:
            if row:
                row_index += 1
                columns = [str(row_index)] + [row[i] for i in range(len(row))]
                data.append(columns)

    return data

def summarizeResults():
    writers = {}

    main_dir = "./results"

    for stat, size in stats.items():
        csv_file = open(f'stats/{stat}_big.csv', 'w')
        writer = csv.writer(csv_file)
        if len(size) == 1:
            writer.writerow(["drift", "imbalance", "speed", "alg", "exp", "instance", stat])
        elif len(size) == 2:
            writer.writerow(["drift", "imbalance", "speed", "alg", "exp", "instance", stat + "_0", stat + "_1"])
        writers[stat] = writer
    for d in drifts:
        path = main_dir + "/" + d

        for unbalance in positives:

            path1 = path + "/" + str(unbalance)

            for alg in os.listdir(path1):
                if "DS_Store" in alg:
                    continue
                path2 = path1 + "/" + alg

                print(f"{d} {unbalance} {alg}")
                # scan 10 experiments:
                for result in os.listdir(path2):
                    if "err" not in result or "DS_Store" in result:
                        continue

                    exp = -1

                    for i in range(n_exp):
                        if str(i) in result:
                            exp = i
                            break
                    assert exp != -1

                    speed = result[:result.index("_")]

                    data = import_csv(path2 + "/" + result)
                    start = False

                    for data_row in data:
                        if data_row[1] == "learning evaluation instances":
                            start = True
                            continue

                        if not start:
                            continue
                        for stat, pos in stats.items():
                            if data_row[pos[0]] == "?":
                                data_row[pos[0]] = "0.0"
                            if len(pos) == 1:

                                writers[stat].writerow(
                                    [d, unbalance, speed, alg, exp, int(float(data_row[1])), float(data_row[pos[0]])])
                            else:
                                if data_row[pos[1]] == "?":
                                    data_row[pos[1]] = "0.0"
                                writers[stat].writerow(
                                    [d, unbalance, speed, alg, exp, int(float(data_row[1])), float(data_row[pos[0]]),
                                     float(data_row[pos[1]])])



if __name__ == '__main__':
    createDir()
    generateArff()
    testfile = createTest()
    buildDocker()
    executeTest()
    summarizeResults()






