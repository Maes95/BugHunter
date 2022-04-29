import sys
import os
import pandas as pd
import graphviz
import pickle
import json
import csv
import copy

sys.path.append('../py')
from framework.utils.GitUtils import GitManager

sys.setrecursionlimit(20000) # Current limit = 999

COLORS = {
    'TestSuccess' : 'green',
    'TestFail' : 'red',
    'TestBuildError' : 'grey',
    'BuildError' : 'black'
}

class CommitGraph():

    def __init__(self, project, bug_id, bug_path, results_dir, root="/home/jovyan/work", restore=False):

        graph_file_path = results_dir+'graph.pickle'

        if restore and os.path.isfile(graph_file_path):
            with open(graph_file_path, 'rb') as handle:
                self.graph = pickle.load(handle)
        else:

            self.graph = {}

            commit_list = []

            # FOR EACH COMMIT
            for _, row in pd.read_csv(bug_path+'commit_history.csv').iterrows():
                commit_path = bug_path+"commits/{id}-{c_hash}/".format(id=row['id'], c_hash=row['hash'])
                if os.path.isfile(commit_path+"result.json"):
                    gm = GitManager(
                        "{root}/projects/{project}_Bug_{bug_id}".format(root=root, bug_id=bug_id, project=project),
                        row['hash']
                    )
                    with open(commit_path+"result.json") as f:
                        raw_result = json.load(f)
                        state = 'TestSuccess'
                        if not raw_result['isSourceBuildSuccess']:
                            state = "BuildError"
                        else:
                            if not raw_result['isTestBuildSuccess']:
                                state = "TestBuildError"
                            else:
                                if not raw_result['isTestExecutionSuccess']:
                                    state = "TestFail"
                        
                        result = {
                            'id': row['id'],
                            'commit': row['hash'],
                            'Build': raw_result['isSourceBuildSuccess'],
                            'BuildTest': raw_result['isTestBuildSuccess'],
                            'ExecuteTest': raw_result['isTestExecutionSuccess'],
                            'HasTestReport': os.path.isfile(commit_path+"test-report.xml"),
                            'State': state,
                            'parents': gm.getParents(row['hash'])
                        }
                        self.graph[row['hash']] = result 
                        commit_list.append(result)

            # SAVE COMMIT HISTORY
            with open(results_dir+"commit_history_results.csv", 'w+') as csvfile: 
                writer = csv.DictWriter(csvfile, fieldnames = commit_list[0].keys()) 
                writer.writeheader()
                writer.writerows(commit_list)

            # ADD CHILDREN INFO
            for result in self.graph.values():
                for parent_hash in result['parents']:
                    if parent_hash == "" or parent_hash not in self.graph: continue
                    if not 'children' in self.graph[parent_hash]:
                        self.graph[parent_hash]['children'] = []
                    self.graph[parent_hash]['children'].append(result['commit'])

            # SAVE GRAPH
            with open(graph_file_path, 'wb') as handle:
                pickle.dump(self.graph, handle, protocol=pickle.HIGHEST_PROTOCOL)

            self.draw_commit_history(commit_list[0]['commit'], results_dir)

    
    def _draw(self, graph, output_dir, filename):
        dot = graphviz.Digraph()

        # Nodes
        for _, result in graph.items():

            node_id = str(result['id'])

            dot.node(result['commit'],node_id,style='filled',fontcolor='white',fillcolor=COLORS[result['State']])

        # Edges
        for _, result in graph.items():
            if result['parents'] is not None:
                for parent in result['parents']:
                    dot.edge(result['commit'], parent)

        dot.format = 'svg'
        dot.render(output_dir+"CommitGraph_"+filename)

    def draw_commit_history(self, fix_commit_hash, output_dir):
        fix_commit = self.graph[fix_commit_hash]
        reduced_graph = reduceGraph(self.graph, fix_commit)
        self._draw(self.graph, output_dir, "Full")
        self._draw(reduced_graph, output_dir, "Reduced")

def bfs(graph, init): 
    visited = []   
    queue = []  
    visited.append(init['commit'])
    queue.append(init['commit'])

    while queue:
        c_hash = queue.pop(0) 
        node = graph[c_hash]         

        for parent_hash in node['parents']:
            if parent_hash not in graph: break
            parent = graph[parent_hash]
            
            if parent['State'] != node['State']:
                if len(node['parents']) >= 2:
                    return node['parents'], list(set(visited) - set(node['parents']))
                else:
                    return [parent_hash], visited
            
            if parent_hash not in visited:
                visited.append(parent_hash)
                queue.append(parent_hash)
    return None, visited

def reduceGraph(old_graph, init):
    visited = list()
    graph = copy.deepcopy(old_graph)
    reduced_graph = {}

    def dfs(visited, graph, node_hash):
        node = graph[node_hash]
        if node['commit'] not in visited:

            visited.append(node['commit'])

            if "" in node['parents']: node['parents'].remove("")

            if len(node['parents']) > 0: 

                if len(node['parents']) == 1:

                    if node['parents'][0] not in graph: 
                        # CASE FOR FAILING FIX                        
                        return node

                    parent = graph[node['parents'][0]]

                    new_parent = dfs(visited, graph, parent['commit'])

                    if new_parent is not None:
                        
                        if new_parent['commit'] not in reduced_graph and len(new_parent['parents']) > 0:
                            antecesor = new_parent['parents'][0]
                            node['parents'] = [antecesor]
                        else:
                            node['parents'] = [new_parent['commit']]

                    if parent['State'] != node['State'] or len(parent['children']) > 1:
                        reduced_graph[node['commit']] = node
                        return node    
                    else:
                        if new_parent is not None and len(new_parent['parents']) > 0:
                            return new_parent                    

                else:
                    reduced_graph[node['commit']] = node

                    new_parents = []
                    for parent_hash in node['parents']:
                        parent = graph[parent_hash]
                        new_parent = dfs(visited, graph, parent['commit'])

                        if new_parent['commit'] not in reduced_graph and len(new_parent['parents']) > 0:
                            antecesor = new_parent['parents'][0]
                            new_parents.append(antecesor)
                        else:
                            new_parents.append(new_parent['commit'])

                    node['parents'] = new_parents

        return node 
                    
    dfs(visited, graph, init['commit'])
    return reduced_graph